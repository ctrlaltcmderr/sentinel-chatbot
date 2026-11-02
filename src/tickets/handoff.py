"""
Handoff Manager - Generates masked handoff summaries for agent transfers.

Creates structured handoff summaries with all PII masked using
mask_sensitive_data() from helpers.
"""

from __future__ import annotations

from src.core.models.data_models import (
    ConversationContext,
    Priority,
    SentimentType,
    SupportTicket,
    TicketStatus,
)
from src.core.utils.helpers import get_logger, mask_sensitive_data, TimeProvider


logger = get_logger("handoff")


class HandoffManager:
    """Generates PII-masked handoff summaries for agent transfers."""

    def generate_summary(
        self,
        ticket: SupportTicket,
        context: ConversationContext,
    ) -> str:
        """
        Generate a structured handoff summary with all PII masked.

        The summary includes:
        - Ticket metadata (ID, status, priority)
        - Issue summary and category
        - Customer sentiment overview
        - Actions already taken (agent messages)
        - Relevant extracted details (order, product)
        - SLA status

        Args:
            ticket: The support ticket being handed off.
            context: The full conversation context.

        Returns:
            A PII-masked handoff summary string.
        """
        sections = []

        # ── Header ──
        sections.append("=" * 60)
        sections.append("AGENT HANDOFF SUMMARY")
        sections.append("=" * 60)

        # ── Ticket info ──
        sections.append(f"\nTicket ID      : {ticket.id}")
        sections.append(f"Status         : {ticket.status.value}")
        sections.append(f"Priority       : {ticket.priority.value} (score: {ticket.priority_score:.2f})")
        sections.append(f"Category       : {ticket.issue_category or 'N/A'}")
        sections.append(f"Assigned Team  : {ticket.assigned_team or 'Unassigned'}")
        sections.append(f"Created        : {ticket.created_at.isoformat()}")

        # ── Customer info ──
        if ticket.customer_name or ticket.customer_email or ticket.customer_phone:
            sections.append(f"\n--- Customer Information ---")
            if ticket.customer_name:
                sections.append(f"Name     : {ticket.customer_name}")
            if ticket.customer_email:
                sections.append(f"Email    : {ticket.customer_email}")
            if ticket.customer_phone:
                sections.append(f"Phone    : {ticket.customer_phone}")

        # ── SLA status ──
        sla_status = "Not set"
        if ticket.sla_breached:
            sla_status = "⚠️  BREACHED"
        elif ticket.sla_deadline:
            remaining = (ticket.sla_deadline - TimeProvider.now()).total_seconds() / 3600.0
            if remaining > 0:
                sla_status = f"{remaining:.1f} hours remaining"
            else:
                sla_status = "⚠️  BREACHED"
        sections.append(f"SLA            : {sla_status}")

        # ── Issue summary ──
        sections.append(f"\n--- Issue Summary ---")
        sections.append(ticket.issue_description or "No description provided.")

        # ── Relevant details ──
        if ticket.order_id or ticket.product:
            sections.append(f"\n--- Relevant Details ---")
            if ticket.order_id:
                sections.append(f"Order ID : {ticket.order_id}")
            if ticket.product:
                sections.append(f"Product  : {ticket.product}")

        # ── Evidence ──
        if ticket.evidence:
            sections.append(f"\n--- Evidence / Attachments ---")
            for i, ev in enumerate(ticket.evidence, 1):
                sections.append(f"  {i}. {ev}")

        # ── Customer sentiment ──
        sections.append(f"\n--- Customer Sentiment ---")
        if context.sentiment_history:
            latest = context.sentiment_history[-1]
            sections.append(f"Current    : {latest.sentiment.value} (confidence: {latest.confidence:.2f})")
            neg_count = sum(
                1 for s in context.sentiment_history
                if s.sentiment in {
                    SentimentType.NEGATIVE,
                    SentimentType.FRUSTRATED,
                    SentimentType.URGENT,
                }
            )
            sections.append(f"Neg. count : {neg_count} of {len(context.sentiment_history)} messages")
            if latest.is_high_risk:
                sections.append(f"⚠️  HIGH RISK: {', '.join(latest.high_risk_triggers)}")
        else:
            sections.append("No sentiment data available.")

        # ── Actions taken (agent messages) ──
        agent_messages = [m for m in context.messages if not m.is_customer]
        if agent_messages:
            sections.append(f"\n--- Actions Taken ---")
            for msg in agent_messages[-5:]:  # Last 5 agent messages
                sections.append(f"  [{msg.timestamp.strftime('%H:%M')}] {msg.content[:200]}")

        # ── Conversation duration ──
        sections.append(f"\n--- Conversation Info ---")
        sections.append(f"Duration   : {context.duration_minutes:.0f} minutes")
        sections.append(f"Messages   : {len(context.messages)} total")
        sections.append(f"Escalated  : {'Yes' if context.is_escalated else 'No'}")

        sections.append("\n" + "=" * 60)

        raw_summary = "\n".join(sections)

        # Mask all PII
        masked_summary = mask_sensitive_data(raw_summary)

        ticket.handoff_summary = masked_summary
        logger.info("Generated handoff summary for ticket %s", ticket.id[:8])

        return masked_summary
