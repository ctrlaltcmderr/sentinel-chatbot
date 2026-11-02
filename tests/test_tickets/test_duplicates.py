"""
Tests for Component 2: Duplicate Detection and Masked Handoff.
"""

import unittest

from src.core.models.data_models import (
    ConversationContext,
    Message,
    Priority,
    SentimentResult,
    SentimentType,
    SupportTicket,
)
from src.tickets.duplicate_detector import DuplicateDetector
from src.tickets.handoff import HandoffManager


class TestDuplicateAndHandoff(unittest.TestCase):
    """Test duplicate detection, grouping, and masked handoffs."""

    def setUp(self):
        self.detector = DuplicateDetector()
        self.handoff = HandoffManager()

    def test_find_duplicates(self):
        t1 = SupportTicket(
            id="t1",
            customer_name="Alice Smith",
            order_id="ORD-12345",
            issue_description="Package was not delivered and tracking is stuck.",
        )
        t2 = SupportTicket(
            id="t2",
            customer_name="Alice Smith",
            order_id="ORD-12345",
            issue_description="Package has not arrived yet, tracking stuck.",
        )
        t3 = SupportTicket(
            id="t3",
            customer_name="Bob Jones",
            order_id="ORD-99999",
            issue_description="Cannot login to my account.",
        )

        duplicates = self.detector.find_duplicates(t2, [t1, t3])
        self.assertEqual(len(duplicates), 1)
        self.assertEqual(duplicates[0].id, "t1")

    def test_group_related_tickets(self):
        t1 = SupportTicket(id="t1", issue_description="Billing charge discrepancy on invoice.")
        t2 = SupportTicket(id="t2", issue_description="Duplicate payment charge on credit card invoice.")
        t3 = SupportTicket(id="t3", issue_description="How do I change my shipping address?")

        groups = self.detector.group_related([t1, t2, t3])
        self.assertGreaterEqual(len(groups), 2)

    def test_masked_handoff_summary(self):
        ctx = ConversationContext()
        ctx.add_message(Message(content="My phone is 987-654-3210 and credit card is 4111 2222 3333 4444."))
        ticket = SupportTicket(
            customer_name="Secret Agent",
            customer_email="agent@cia.gov",
            issue_description="Need password reset. Phone 987-654-3210.",
            priority=Priority.HIGH,
        )

        summary = self.handoff.generate_summary(ticket, ctx)
        self.assertNotIn("4111 2222 3333 4444", summary)
        self.assertIn("***MASKED***", summary)

    def test_separate_unrelated_issues(self):
        """Test separating multiple unrelated issues raised within a single conversation."""
        msgs = [
            Message(content="My router is not turning on.", is_customer=True),
            Message(content="We can help with that. Have you checked the power cable?", is_customer=False),
            Message(content="By the way, on another note, my billing charge this month was doubled.", is_customer=True),
            Message(content="I also noticed that another issue is my warranty document has a typo.", is_customer=True),
        ]
        groups = self.detector.separate_unrelated(msgs)
        self.assertGreaterEqual(len(groups), 2)
        # First group should have the router issue
        self.assertIn("router", groups[0][0].content.lower())


if __name__ == "__main__":
    unittest.main()
