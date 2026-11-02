"""
Priority Calculator - Calculates ticket priority from weighted factors.

Uses a configurable weighted scoring system considering severity,
sentiment, waiting time, customer impact, and SLA urgency.
"""

from __future__ import annotations

from typing import Tuple

from src.core.models.data_models import (
    ConversationContext,
    Priority,
    SentimentResult,
    SentimentType,
    SupportTicket,
)
from src.core.config.settings import get_settings
from src.core.utils.helpers import get_logger, TimeProvider


logger = get_logger("priority_calculator")

# High-severity issue keywords that increase the severity score
_SEVERITY_KEYWORDS = {
    "critical": [
        "account compromise", "hacked", "unauthorized access", "fraud",
        "stolen", "identity theft", "data breach", "security breach",
    ],
    "high": [
        "double charged", "duplicate payment", "legal action", "lawyer",
        "lawsuit", "court", "attorney", "not working at all",
        "completely broken", "lost data", "urgent",
    ],
    "medium": [
        "error", "bug", "slow", "delayed", "wrong", "missing",
        "broken", "crash", "failed",
    ],
}

# Categories with inherent higher risk
_HIGH_RISK_CATEGORIES = {"account_security", "billing"}


class PriorityCalculator:
    """Calculates ticket priority using weighted scoring factors."""

    def __init__(self, settings=None):
        self.settings = settings or get_settings()
        self._weights = self.settings.tickets.severity_weights

    def calculate(
        self,
        ticket: SupportTicket,
        sentiment: SentimentResult,
        context: ConversationContext,
    ) -> Tuple[Priority, float]:
        """
        Calculate ticket priority from multiple weighted factors.

        Factors and default weights:
        - severity (0.30): Issue severity based on keywords and category
        - sentiment (0.25): Customer sentiment analysis results
        - waiting_time (0.15): How long the customer has been waiting
        - customer_impact (0.20): Breadth/depth of customer impact
        - sla_urgency (0.10): How close to SLA breach

        Args:
            ticket: The support ticket to prioritise.
            sentiment: Sentiment analysis result for the conversation.
            context: The full conversation context.

        Returns:
            Tuple of (Priority enum, raw score 0.0-1.0).
        """
        # Re-read weights in case of runtime updates
        weights = self.settings.tickets.severity_weights

        severity_score = self._calculate_severity(ticket)
        sentiment_score = self._calculate_sentiment_score(sentiment, context)
        waiting_score = self._calculate_waiting_time_score(context)
        impact_score = self._calculate_customer_impact(ticket, context)
        sla_score = self._calculate_sla_urgency(ticket)

        raw_score = (
            weights.get("severity", 0.30) * severity_score
            + weights.get("sentiment", 0.25) * sentiment_score
            + weights.get("waiting_time", 0.15) * waiting_score
            + weights.get("customer_impact", 0.20) * impact_score
            + weights.get("sla_urgency", 0.10) * sla_score
        )

        # High-risk security / legal issues guarantee critical priority
        if sentiment.is_high_risk and severity_score >= 0.9:
            raw_score = max(raw_score, 0.85)

        # Clamp to [0, 1]
        raw_score = max(0.0, min(1.0, raw_score))

        priority = self._score_to_priority(raw_score)

        logger.info(
            "Priority for ticket %s: %s (score=%.3f) "
            "[sev=%.2f sent=%.2f wait=%.2f imp=%.2f sla=%.2f]",
            ticket.id[:8], priority.value, raw_score,
            severity_score, sentiment_score, waiting_score,
            impact_score, sla_score,
        )

        return priority, raw_score

    # ───────────────────── Factor calculators ─────────────────────

    def _calculate_severity(self, ticket: SupportTicket) -> float:
        """Score 0-1 based on issue keywords and category."""
        text = (ticket.issue_description + " " + ticket.issue_category).lower()
        score = 0.0

        # Keyword-based severity
        for kw in _SEVERITY_KEYWORDS["critical"]:
            if kw in text:
                score = max(score, 1.0)
                break
        if score < 1.0:
            for kw in _SEVERITY_KEYWORDS["high"]:
                if kw in text:
                    score = max(score, 0.75)
                    break
        if score < 0.75:
            for kw in _SEVERITY_KEYWORDS["medium"]:
                if kw in text:
                    score = max(score, 0.5)
                    break

        # Category-based boost
        if ticket.issue_category in _HIGH_RISK_CATEGORIES:
            score = max(score, 0.6)

        return score

    def _calculate_sentiment_score(
        self, sentiment: SentimentResult, context: ConversationContext
    ) -> float:
        """Score 0-1 based on sentiment analysis."""
        base_scores = {
            SentimentType.URGENT: 1.0,
            SentimentType.FRUSTRATED: 0.85,
            SentimentType.NEGATIVE: 0.7,
            SentimentType.SARCASTIC: 0.6,
            SentimentType.NEUTRAL: 0.3,
            SentimentType.POSITIVE: 0.1,
        }
        score = base_scores.get(sentiment.sentiment, 0.3)

        # Boost for high-risk triggers
        if sentiment.is_high_risk:
            score = max(score, 0.9)

        # Boost for repeated negative sentiment in history
        negative_types = {
            SentimentType.NEGATIVE, SentimentType.FRUSTRATED, SentimentType.URGENT
        }
        neg_count = sum(
            1 for s in context.sentiment_history
            if s.sentiment in negative_types
        )
        if neg_count >= 3:
            score = min(1.0, score + 0.15)
        elif neg_count >= 2:
            score = min(1.0, score + 0.05)

        return score

    def _calculate_waiting_time_score(self, context: ConversationContext) -> float:
        """Score 0-1 based on how long customer has been waiting."""
        duration = context.duration_minutes
        if duration >= 60:
            return 1.0
        elif duration >= 30:
            return 0.75
        elif duration >= 15:
            return 0.5
        elif duration >= 5:
            return 0.25
        return 0.1

    def _calculate_customer_impact(
        self, ticket: SupportTicket, context: ConversationContext
    ) -> float:
        """Score 0-1 based on breadth of customer impact."""
        score = 0.3  # baseline

        # Multiple related tickets indicate recurring issues
        if ticket.related_tickets:
            score = min(1.0, score + 0.15 * len(ticket.related_tickets))

        # Financial impact keywords
        text_lower = ticket.issue_description.lower()
        financial_keywords = [
            "money", "charged", "payment", "refund", "lost",
            "stolen", "fraud", "billing",
        ]
        financial_hits = sum(1 for kw in financial_keywords if kw in text_lower)
        if financial_hits >= 2:
            score = min(1.0, score + 0.3)
        elif financial_hits >= 1:
            score = min(1.0, score + 0.15)

        # Long conversations indicate complex issues
        if len(context.messages) >= 10:
            score = min(1.0, score + 0.15)
        elif len(context.messages) >= 5:
            score = min(1.0, score + 0.05)

        return score

    def _calculate_sla_urgency(self, ticket: SupportTicket) -> float:
        """Score 0-1 based on proximity to SLA deadline."""
        if ticket.sla_breached:
            return 1.0
        if ticket.sla_deadline is None:
            return 0.2  # No SLA set yet

        now = TimeProvider.now()
        remaining = (ticket.sla_deadline - now).total_seconds() / 3600.0

        if remaining <= 0:
            return 1.0
        elif remaining <= 1:
            return 0.9
        elif remaining <= 2:
            return 0.7
        elif remaining <= 4:
            return 0.5
        return 0.2

    @staticmethod
    def _score_to_priority(score: float) -> Priority:
        """Map a 0-1 score to a Priority enum."""
        if score > 0.8:
            return Priority.CRITICAL
        elif score > 0.6:
            return Priority.HIGH
        elif score > 0.4:
            return Priority.MEDIUM
        else:
            return Priority.LOW
