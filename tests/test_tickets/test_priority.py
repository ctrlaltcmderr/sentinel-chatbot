"""
Tests for Component 2: Priority Calculator.
"""

import unittest
from datetime import datetime, timedelta

from src.core.models.data_models import (
    ConversationContext,
    Message,
    Priority,
    SentimentResult,
    SentimentType,
    SupportTicket,
)
from src.core.utils.helpers import TimeProvider
from src.tickets.priority_calculator import PriorityCalculator


class TestPriorityCalculator(unittest.TestCase):
    """Test priority calculation with weights."""

    def setUp(self):
        self.calculator = PriorityCalculator()
        TimeProvider.reset()

    def tearDown(self):
        TimeProvider.reset()

    def test_critical_priority_high_risk(self):
        ctx = ConversationContext()
        ticket = SupportTicket(
            issue_category="account_security",
            issue_description="Someone hacked my account and made unauthorized access.",
        )
        sentiment = SentimentResult(
            sentiment=SentimentType.URGENT,
            is_high_risk=True,
            high_risk_triggers=["hacked", "account compromise"],
        )
        priority, score = self.calculator.calculate(ticket, sentiment, ctx)
        self.assertEqual(priority, Priority.CRITICAL)
        self.assertGreater(score, 0.75)

    def test_low_priority_routine_inquiry(self):
        ctx = ConversationContext()
        ticket = SupportTicket(
            issue_category="general",
            issue_description="Just checking my order delivery status.",
        )
        sentiment = SentimentResult(
            sentiment=SentimentType.POSITIVE,
            is_high_risk=False,
        )
        priority, score = self.calculator.calculate(ticket, sentiment, ctx)
        self.assertIn(priority, (Priority.LOW, Priority.MEDIUM))
        self.assertLess(score, 0.5)


if __name__ == "__main__":
    unittest.main()
