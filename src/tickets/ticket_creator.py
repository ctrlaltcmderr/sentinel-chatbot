"""
Ticket Creator - Extracts structured ticket data from conversation context.

Creates SupportTicket instances from conversations by extracting customer info,
order details, product info, issue descriptions, evidence, and contact details.
Identifies and reports missing mandatory fields.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Set

from src.core.models.data_models import (
    ConversationContext,
    Message,
    SupportTicket,
    TicketStatus,
)
from src.core.config.settings import get_settings
from src.core.utils.helpers import (
    extract_patterns,
    generate_id,
    get_logger,
    TimeProvider,
)


logger = get_logger("ticket_creator")

# ────────────────── Issue-category keyword mapping ──────────────────
_CATEGORY_KEYWORDS: Dict[str, List[str]] = {
    "billing": [
        "charge", "charged", "payment", "refund", "invoice", "bill",
        "subscription", "double charged", "overcharged", "credit",
        "debit", "fee", "pricing", "cost", "receipt",
    ],
    "technical": [
        "error", "bug", "crash", "not working", "broken", "slow",
        "loading", "glitch", "freeze", "update", "install",
        "unresponsive", "timeout", "exception", "fails",
    ],
    "account_security": [
        "hack", "hacked", "compromised", "unauthorized", "password",
        "login", "locked out", "two-factor", "2fa", "suspicious",
        "identity theft", "fraud", "stolen", "phishing",
        "without permission", "accessed my account", "unauthorized access",
        "unauthorized payment", "unauthorized charge", "security breach",
        "account takeover",
    ],
    "shipping": [
        "delivery", "shipped", "shipping", "tracking", "lost package",
        "delayed", "wrong address", "return", "parcel", "courier",
        "not received", "damaged package",
    ],
}

# Evidence-related keywords
_EVIDENCE_KEYWORDS: List[str] = [
    "screenshot", "attachment", "photo", "image", "picture",
    "video", "document", "file", "pdf", "receipt", "proof",
    "log", "recording",
]

# Name-introduction patterns
_NAME_PATTERNS: List[re.Pattern] = [
    re.compile(r"(?:my name is|i'm|i am|this is)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", re.IGNORECASE),
    re.compile(r"(?:name|customer)[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", re.IGNORECASE),
]

# Product patterns
_PRODUCT_PATTERNS: List[re.Pattern] = [
    re.compile(r"(?:product|item|device|model|service)[:\s]+([A-Za-z0-9\s]+?)(?:\.|,|$)", re.IGNORECASE),
    re.compile(r"(?:using|bought|purchased|ordered)\s+(?:a\s+|an\s+|the\s+)?([A-Za-z0-9]+(?:\s+[A-Za-z0-9]+){0,3})", re.IGNORECASE),
]


class TicketCreator:
    """Creates structured support tickets from conversation context."""

    def __init__(self, settings=None):
        self.settings = settings or get_settings()
        self._config = self.settings.tickets

    def create_from_conversation(self, context: ConversationContext) -> SupportTicket:
        """
        Create a support ticket from a conversation context.

        Extracts customer info, order details, product info, issue description,
        evidence, and contact details from the conversation messages.

        Args:
            context: The conversation context to extract from.

        Returns:
            A populated SupportTicket with missing_fields indicating
            any mandatory fields that could not be extracted.
        """
        ticket = SupportTicket(
            id=generate_id(),
            session_id=context.session_id,
            customer_id=context.customer_id,
            created_at=TimeProvider.now(),
            updated_at=TimeProvider.now(),
        )

        # Combine all customer messages for pattern extraction
        customer_messages = [
            m for m in context.messages if m.is_customer
        ]
        full_text = " ".join(m.content for m in customer_messages)

        # ── Extract structured patterns ──
        patterns = extract_patterns(full_text)

        # Order ID
        if "order_ids" in patterns and patterns["order_ids"]:
            ticket.order_id = patterns["order_ids"][0]

        # Contact email
        if "emails" in patterns and patterns["emails"]:
            ticket.customer_email = patterns["emails"][0]

        # Contact phone
        if "phone_numbers" in patterns and patterns["phone_numbers"]:
            ticket.customer_phone = patterns["phone_numbers"][0]

        # Product codes
        if "product_codes" in patterns and patterns["product_codes"]:
            ticket.product = patterns["product_codes"][0]

        # ── Extract customer name ──
        ticket.customer_name = self._extract_customer_name(customer_messages)

        # ── Extract product info (broader matching) ──
        if not ticket.product:
            ticket.product = self._extract_product(customer_messages)

        # ── Extract issue description ──
        ticket.issue_description = self._extract_issue_description(customer_messages)

        # ── Determine issue category ──
        ticket.issue_category = self._classify_issue(full_text)

        # ── Extract evidence references ──
        ticket.evidence = self._extract_evidence(customer_messages)

        # ── Collect attachments from messages ──
        for msg in customer_messages:
            for att in msg.attachments:
                if att not in ticket.evidence:
                    ticket.evidence.append(att)

        # ── Build conversation summary ──
        ticket.conversation_summary = self._build_summary(customer_messages)

        # ── Store extracted metadata ──
        ticket.metadata["extracted_patterns"] = patterns

        # ── Identify missing mandatory fields ──
        ticket.missing_fields = self._check_mandatory_fields(ticket)

        logger.info(
            "Created ticket %s from session %s (missing: %s)",
            ticket.id[:8], context.session_id[:8], ticket.missing_fields,
        )
        return ticket

    def request_missing_info(self, ticket: SupportTicket) -> str:
        """
        Generate a polite message asking the customer for missing mandatory fields.

        Args:
            ticket: The ticket with missing_fields populated.

        Returns:
            A customer-facing message requesting the missing information.
        """
        if not ticket.missing_fields:
            return ""

        field_descriptions = {
            "customer_name": "your full name",
            "issue_description": "a description of the issue you're experiencing",
            "contact_email": "your email address for follow-up",
        }

        parts = []
        for f in ticket.missing_fields:
            desc = field_descriptions.get(f, f.replace("_", " "))
            parts.append(desc)

        if len(parts) == 1:
            items = parts[0]
        elif len(parts) == 2:
            items = f"{parts[0]} and {parts[1]}"
        else:
            items = ", ".join(parts[:-1]) + f", and {parts[-1]}"

        return (
            f"Thank you for reaching out! To help resolve your issue quickly, "
            f"could you please provide {items}?"
        )

    # ──────────────────────── Private helpers ────────────────────────

    def _extract_customer_name(self, messages: List[Message]) -> str:
        """Extract customer name from messages using patterns."""
        for msg in messages:
            for pattern in _NAME_PATTERNS:
                match = pattern.search(msg.content)
                if match:
                    name = match.group(1).strip()
                    # Basic validation: at least 2 chars, not a common word
                    if len(name) >= 2 and name.lower() not in {
                        "the", "and", "for", "not", "you", "your",
                    }:
                        return name
        return ""

    def _extract_product(self, messages: List[Message]) -> str:
        """Extract product name from messages."""
        for msg in messages:
            for pattern in _PRODUCT_PATTERNS:
                match = pattern.search(msg.content)
                if match:
                    product = match.group(1).strip()
                    if len(product) >= 2:
                        return product
        return ""

    def _extract_issue_description(self, messages: List[Message]) -> str:
        """
        Extract the issue description from customer messages.
        Uses the longest customer message as the primary description,
        or concatenates all if they're short.
        """
        if not messages:
            return ""

        # Find the longest substantive message
        substantive = [
            m.content for m in messages
            if len(m.content) > 10 and not m.content.strip().startswith("hi")
        ]
        if substantive:
            return max(substantive, key=len).strip()

        # Fallback: use all message content
        all_content = " ".join(m.content.strip() for m in messages if m.content.strip())
        return all_content if len(all_content) > 5 else ""

    def _classify_issue(self, text: str) -> str:
        """Classify the issue into a category based on keyword matching."""
        text_lower = text.lower()
        scores: Dict[str, int] = {}

        for category, keywords in _CATEGORY_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > 0:
                scores[category] = score

        if scores:
            # Security incidents (account compromise, fraud, unauthorized access) take precedence
            if scores.get("account_security", 0) > 0 and scores["account_security"] >= max(scores.values()) - 1:
                return "account_security"
            return max(scores, key=scores.get)
        return "general"

    def _extract_evidence(self, messages: List[Message]) -> List[str]:
        """Extract references to evidence (screenshots, attachments, etc.)."""
        evidence: List[str] = []
        for msg in messages:
            text_lower = msg.content.lower()
            for kw in _EVIDENCE_KEYWORDS:
                if kw in text_lower:
                    # Extract the sentence containing the keyword
                    sentences = re.split(r"[.!?]", msg.content)
                    for sentence in sentences:
                        if kw in sentence.lower() and sentence.strip():
                            ref = sentence.strip()
                            if ref not in evidence:
                                evidence.append(ref)
                    break  # Only check once per message
        return evidence

    def _build_summary(self, messages: List[Message]) -> str:
        """Build a brief conversation summary from customer messages."""
        if not messages:
            return ""
        content_parts = []
        for msg in messages[:5]:  # First 5 messages
            truncated = msg.content[:150].strip()
            if truncated:
                content_parts.append(truncated)
        return " | ".join(content_parts)

    def _check_mandatory_fields(self, ticket: SupportTicket) -> List[str]:
        """Check which mandatory fields are missing."""
        missing: List[str] = []
        field_map = {
            "customer_name": ticket.customer_name,
            "issue_description": ticket.issue_description,
            "contact_email": ticket.customer_email,
        }
        for field_name in self._config.mandatory_fields:
            value = field_map.get(field_name, "")
            if not value or not value.strip():
                missing.append(field_name)
        return missing
