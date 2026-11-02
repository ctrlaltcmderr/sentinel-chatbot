"""
Escalation Manager for Sentinel Chatbot.

Determines when a conversation should be escalated to a human agent
based on sentiment patterns, high-risk keywords, time conditions,
and business hours rules.
"""

from __future__ import annotations

from datetime import datetime
import re
from typing import Optional

from src.core.config.settings import get_settings, Settings
from src.core.models.data_models import (
    ConversationContext,
    EscalationReason,
    EscalationRecord,
    Priority,
    SentimentResult,
    SentimentType,
)
from src.core.utils.helpers import TimeProvider, get_logger


logger = get_logger("sentiment.escalation")

# Sentiment types considered "negative" for escalation purposes
_NEGATIVE_SENTIMENTS = {
    SentimentType.NEGATIVE,
    SentimentType.FRUSTRATED,
    SentimentType.URGENT,
    SentimentType.SARCASTIC,
}


class EscalationManager:
    """
    Manages escalation logic for customer conversations.

    Trigger conditions
    ------------------
    a) 3+ consecutive negative/frustrated messages → escalate
    b) High-risk issue detected → immediate escalation regardless of tone
    c) Urgent complaint outside business hours → on-call queue
    d) Normal complaint outside business hours → schedule next business day
    e) Negative conversation unresolved > 15 minutes → auto-escalate
    """

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        self.config = self.settings.sentiment
        self.business_hours = self.settings.business_hours

    def check_escalation(
        self,
        context: ConversationContext,
        sentiment: SentimentResult,
    ) -> Optional[EscalationRecord]:
        """
        Evaluate whether the conversation should be escalated.

        Checks are run in priority order; the first triggered condition
        produces the escalation record.

        Returns None when no escalation is needed.
        """
        now = TimeProvider.now()
        is_bh = self.business_hours.is_business_hours(now)

        # ── Condition B: High-risk issue (always highest priority) ──
        record = self._check_high_risk(context, sentiment, now, is_bh)
        if record:
            return record

        # ── Explicit Customer Request for Human Handoff / Ticket ──
        record = self._check_customer_request(context, sentiment, now, is_bh)
        if record:
            return record

        # ── Conditions C/D: After-hours routing ──
        record = self._check_after_hours(context, sentiment, now, is_bh)
        if record:
            return record

        # ── Condition A: Consecutive negative sentiments ──
        record = self._check_consecutive_negative(context, sentiment, now, is_bh)
        if record:
            return record

        # ── Condition E: Unresolved negative > 15 minutes ──
        record = self._check_unresolved_timeout(context, sentiment, now, is_bh)
        if record:
            return record

        return None

    # ──────────────────────── Condition Checks ────────────────────────

    def _check_high_risk(
        self,
        context: ConversationContext,
        sentiment: SentimentResult,
        now: datetime,
        is_bh: bool,
    ) -> Optional[EscalationRecord]:
        """Condition B: High-risk keywords trigger immediate escalation."""
        if not sentiment.is_high_risk:
            return None

        summary = self._build_summary(context)
        queue_type = "standard" if is_bh else "on_call"

        record = EscalationRecord(
            session_id=context.session_id,
            reason=EscalationReason.HIGH_RISK_ISSUE,
            activated_condition=(
                f"High-risk keywords detected: {', '.join(sentiment.high_risk_triggers)}"
            ),
            conversation_summary=summary,
            sentiment_at_escalation=sentiment,
            priority=Priority.CRITICAL,
            timestamp=now,
            queue_type=queue_type,
        )
        logger.warning(
            "HIGH-RISK escalation triggered: %s", sentiment.high_risk_triggers
        )
        return record

    def _check_customer_request(
        self,
        context: ConversationContext,
        sentiment: SentimentResult,
        now: datetime,
        is_bh: bool,
    ) -> Optional[EscalationRecord]:
        """Customer explicitly requests a human agent or support ticket."""
        if not context.messages:
            return None
        last_msg = context.messages[-1].content.lower()
        patterns = [
            r"\b(?:connect|transfer|speak|talk)\s+(?:me\s+)?(?:with|to)\s+(?:a\s+)?(?:person|human|agent|representative|specialist|operator)\b",
            r"\b(?:speak|talk)\s+to\s+(?:someone|somebody|a\s+human|an\s+agent)\b",
            r"\b(?:need|want)\s+(?:a\s+)?(?:person|human|human\s+agent|real\s+person)\b",
            r"\b(?:open|create|submit)\s+(?:a\s+)?ticket\b",
            r"\bescalat(?:e|ion)\s+to\s+(?:a\s+)?(?:human|person|agent|team)\b",
        ]
        if any(re.search(pat, last_msg) for pat in patterns):
            queue_type = "standard" if is_bh else "on_call"
            summary = self._build_summary(context)
            record = EscalationRecord(
                session_id=context.session_id,
                reason=EscalationReason.CUSTOMER_REQUEST,
                activated_condition="Customer explicitly requested human agent handoff or ticket creation",
                conversation_summary=summary,
                sentiment_at_escalation=sentiment,
                priority=Priority.HIGH,
                timestamp=now,
                queue_type=queue_type,
            )
            logger.info("Customer requested human escalation / ticket creation.")
            return record
        return None

    def _check_consecutive_negative(
        self,
        context: ConversationContext,
        sentiment: SentimentResult,
        now: datetime,
        is_bh: bool,
    ) -> Optional[EscalationRecord]:
        """Condition A: 3+ consecutive negative/frustrated messages."""
        threshold = self.config.escalation_negative_count  # default 3

        # Build the full sentiment list including the current one
        history = list(context.sentiment_history) + [sentiment]

        # Count consecutive negatives from the end
        consecutive = 0
        for s in reversed(history):
            if s.sentiment in _NEGATIVE_SENTIMENTS:
                consecutive += 1
            else:
                break

        if consecutive < threshold:
            return None

        summary = self._build_summary(context)
        queue_type = "standard" if is_bh else "on_call"

        record = EscalationRecord(
            session_id=context.session_id,
            reason=EscalationReason.REPEATED_NEGATIVE,
            activated_condition=(
                f"{consecutive} consecutive negative/frustrated messages "
                f"(threshold: {threshold})"
            ),
            conversation_summary=summary,
            sentiment_at_escalation=sentiment,
            priority=Priority.HIGH,
            timestamp=now,
            queue_type=queue_type,
        )
        logger.warning(
            "Consecutive-negative escalation: %d messages", consecutive
        )
        return record

    def _check_unresolved_timeout(
        self,
        context: ConversationContext,
        sentiment: SentimentResult,
        now: datetime,
        is_bh: bool,
    ) -> Optional[EscalationRecord]:
        """Condition E: Negative conversation unresolved > 15 minutes."""
        if context.is_resolved:
            return None

        timeout = self.config.unresolved_escalation_minutes  # default 15

        # Check if conversation has any negative sentiment in history
        has_negative = any(
            s.sentiment in _NEGATIVE_SENTIMENTS
            for s in context.sentiment_history
        ) or sentiment.sentiment in _NEGATIVE_SENTIMENTS

        if not has_negative:
            return None

        # Calculate duration from conversation start to now
        duration_minutes = (now - context.started_at).total_seconds() / 60

        if duration_minutes < timeout:
            return None

        summary = self._build_summary(context)
        queue_type = "standard" if is_bh else "on_call"

        record = EscalationRecord(
            session_id=context.session_id,
            reason=EscalationReason.UNRESOLVED_TIMEOUT,
            activated_condition=(
                f"Negative conversation unresolved for {duration_minutes:.1f} minutes "
                f"(threshold: {timeout} minutes)"
            ),
            conversation_summary=summary,
            sentiment_at_escalation=sentiment,
            priority=Priority.HIGH,
            timestamp=now,
            queue_type=queue_type,
        )
        logger.warning(
            "Unresolved-timeout escalation: %.1f minutes", duration_minutes
        )
        return record

    def _check_after_hours(
        self,
        context: ConversationContext,
        sentiment: SentimentResult,
        now: datetime,
        is_bh: bool,
    ) -> Optional[EscalationRecord]:
        """
        Conditions C/D: After-hours routing.
        - Urgent complaint → on-call queue
        - Normal complaint → schedule next business day
        """
        if is_bh:
            return None

        # Only escalate if there's a complaint (negative/frustrated/urgent)
        is_complaint = sentiment.sentiment in _NEGATIVE_SENTIMENTS

        if not is_complaint:
            return None

        summary = self._build_summary(context)

        # Condition C: Urgent after-hours → on-call
        if sentiment.sentiment == SentimentType.URGENT:
            record = EscalationRecord(
                session_id=context.session_id,
                reason=EscalationReason.AFTER_HOURS_URGENT,
                activated_condition=(
                    "Urgent complaint received outside business hours — "
                    "routing to on-call queue"
                ),
                conversation_summary=summary,
                sentiment_at_escalation=sentiment,
                priority=Priority.CRITICAL,
                timestamp=now,
                queue_type="on_call",
            )
            logger.warning("After-hours URGENT escalation → on-call queue")
            return record

        # Condition D: Non-urgent complaint after-hours → next business day
        next_bd = self.business_hours.next_business_day(now)
        record = EscalationRecord(
            session_id=context.session_id,
            reason=EscalationReason.AFTER_HOURS_URGENT,
            activated_condition=(
                f"Complaint received outside business hours — "
                f"scheduled for next business day: {next_bd.strftime('%Y-%m-%d %H:%M')}"
            ),
            conversation_summary=summary,
            sentiment_at_escalation=sentiment,
            priority=Priority.MEDIUM,
            timestamp=now,
            queue_type="next_business_day",
        )
        logger.info("After-hours complaint → next business day: %s", next_bd)
        return record

    # ──────────────────────── Helpers ────────────────────────

    @staticmethod
    def _build_summary(context: ConversationContext) -> str:
        """Build a conversation summary for the escalation record."""
        if context.summary:
            return context.summary

        messages = context.messages
        if not messages:
            return "No messages in conversation."

        # Take last few messages for a brief summary
        recent = messages[-5:]
        lines = []
        for msg in recent:
            role = "Customer" if msg.is_customer else "Agent"
            snippet = msg.content[:120]
            if len(msg.content) > 120:
                snippet += "..."
            lines.append(f"[{role}] {snippet}")

        return " | ".join(lines)
