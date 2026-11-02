"""
Duplicate Detector - Finds duplicate and related tickets.

Compares tickets by customer, issue description similarity,
and order IDs.  Also groups related tickets and separates
unrelated issues within a single conversation.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Set, Tuple

from src.core.models.data_models import Message, SupportTicket
from src.core.utils.helpers import get_logger, normalize_text


logger = get_logger("duplicate_detector")

# Minimum similarity to consider duplicates
_DUPLICATE_THRESHOLD = 0.5
# Minimum similarity to consider related
_RELATED_THRESHOLD = 0.3


class DuplicateDetector:
    """Detects duplicate and related support tickets."""

    def __init__(self, duplicate_threshold: float = _DUPLICATE_THRESHOLD,
                 related_threshold: float = _RELATED_THRESHOLD):
        self._dup_threshold = duplicate_threshold
        self._rel_threshold = related_threshold

    def find_duplicates(
        self,
        ticket: SupportTicket,
        existing: List[SupportTicket],
    ) -> List[SupportTicket]:
        """
        Find existing tickets that are likely duplicates of the given ticket.

        A ticket is considered a duplicate when *any* of:
        - Same customer AND similar issue description
        - Same non-empty order_id AND similar issue description
        - Same customer AND same order_id

        Args:
            ticket: The new ticket to check.
            existing: List of existing tickets to compare against.

        Returns:
            List of likely duplicate tickets, ordered by similarity
            (most similar first).
        """
        duplicates: List[Tuple[SupportTicket, float]] = []

        for other in existing:
            if other.id == ticket.id:
                continue

            score = self._duplicate_score(ticket, other)
            if score >= self._dup_threshold:
                duplicates.append((other, score))

        # Sort by score descending
        duplicates.sort(key=lambda x: x[1], reverse=True)
        result = [t for t, _ in duplicates]

        if result:
            logger.info(
                "Found %d duplicate(s) for ticket %s",
                len(result), ticket.id[:8],
            )

        return result

    def group_related(
        self, tickets: List[SupportTicket]
    ) -> List[List[SupportTicket]]:
        """
        Group tickets that are related to each other.

        Uses union-find to cluster tickets with similarity above the
        related threshold.

        Args:
            tickets: All tickets to group.

        Returns:
            List of groups, where each group is a list of related tickets.
        """
        n = len(tickets)
        if n == 0:
            return []

        # Union-find
        parent = list(range(n))

        def find(x: int) -> int:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a: int, b: int) -> None:
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb

        for i in range(n):
            for j in range(i + 1, n):
                score = self._related_score(tickets[i], tickets[j])
                if score >= self._rel_threshold:
                    union(i, j)

        groups: Dict[int, List[SupportTicket]] = {}
        for i in range(n):
            root = find(i)
            groups.setdefault(root, []).append(tickets[i])

        return list(groups.values())

    def separate_unrelated(
        self, messages: List[Message]
    ) -> List[List[Message]]:
        """
        Split a conversation's messages into sub-conversations
        when the customer raises multiple unrelated issues.

        Detection heuristic:
        - Look for topic-shift signals (e.g. "another issue",
          "also", "by the way", "different problem").
        - When a shift is detected, start a new group.

        Args:
            messages: Ordered list of messages in a conversation.

        Returns:
            List of message groups, each representing a distinct issue.
        """
        if not messages:
            return []

        _TOPIC_SHIFT_PATTERNS = [
            re.compile(r"\b(?:another|separate|different)\s+(?:issue|problem|question|concern|matter)\b", re.IGNORECASE),
            re.compile(r"\b(?:also|additionally|by the way|btw|one more thing|secondly|on another note)\b", re.IGNORECASE),
            re.compile(r"\b(?:unrelated|new topic|switching topic|change of subject)\b", re.IGNORECASE),
        ]

        groups: List[List[Message]] = [[]]

        for msg in messages:
            if msg.is_customer:
                shift_detected = any(
                    p.search(msg.content) for p in _TOPIC_SHIFT_PATTERNS
                )
                if shift_detected and groups[-1]:
                    groups.append([])
            groups[-1].append(msg)

        # Filter out empty groups
        return [g for g in groups if g]

    # ──────────────────── Private helpers ────────────────────

    def _duplicate_score(self, a: SupportTicket, b: SupportTicket) -> float:
        """
        Calculate a duplicate likelihood score between 0 and 1.

        Components:
        - Same customer: +0.3
        - Same order_id (non-empty): +0.3
        - Issue description similarity: up to 0.4
        """
        score = 0.0

        same_customer = self._same_customer(a, b)
        same_order = (
            a.order_id and b.order_id and
            a.order_id.strip().lower() == b.order_id.strip().lower()
        )
        desc_sim = self._text_similarity(a.issue_description, b.issue_description)

        if same_customer:
            score += 0.3
        if same_order:
            score += 0.3

        score += 0.4 * desc_sim

        return score

    def _related_score(self, a: SupportTicket, b: SupportTicket) -> float:
        """Score relatedness between two tickets."""
        score = 0.0

        if self._same_customer(a, b):
            score += 0.2
        if a.issue_category and b.issue_category and a.issue_category == b.issue_category:
            score += 0.2
        if a.product and b.product and a.product.lower() == b.product.lower():
            score += 0.15

        desc_sim = self._text_similarity(a.issue_description, b.issue_description)
        score += 0.45 * desc_sim

        same_order = (
            a.order_id and b.order_id and
            a.order_id.strip().lower() == b.order_id.strip().lower()
        )
        if same_order:
            score += 0.2

        return min(1.0, score)

    @staticmethod
    def _same_customer(a: SupportTicket, b: SupportTicket) -> bool:
        """Check if two tickets belong to the same customer."""
        if a.customer_id and b.customer_id:
            return a.customer_id == b.customer_id
        if a.customer_email and b.customer_email:
            return a.customer_email.lower() == b.customer_email.lower()
        if a.customer_name and b.customer_name:
            return normalize_text(a.customer_name) == normalize_text(b.customer_name)
        return False

    @staticmethod
    def _text_similarity(text1: str, text2: str) -> float:
        """
        Simple word-overlap (Jaccard) similarity between two texts.
        Returns a value between 0 and 1.
        """
        if not text1 or not text2:
            return 0.0

        words1 = set(normalize_text(text1).split())
        words2 = set(normalize_text(text2).split())

        if not words1 or not words2:
            return 0.0

        intersection = words1 & words2
        union = words1 | words2
        return len(intersection) / len(union)
