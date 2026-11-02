"""
Tests for Component 1: Escalation Manager.

Covers:
- Consecutive negative message escalation
- High-risk issue detection (calm high-risk complaints, legal threats, duplicate payments)
- After-hours urgent routing to on-call queue
- After-hours normal complaint scheduled for next business day
- 15-minute unresolved negative conversation auto-escalation
- Simulated time changes using TimeProvider
- Escalation record structure completeness
"""

import unittest
from datetime import datetime, timedelta

from src.core.config.settings import get_settings
from src.core.models.data_models import (
    ConversationContext,
    EscalationReason,
    Message,
    Priority,
    SentimentResult,
    SentimentType,
)
from src.core.utils.helpers import TimeProvider
from src.sentiment.analyzer import SentimentAnalyzer
from src.sentiment.escalation import EscalationManager


class TestEscalationManager(unittest.TestCase):
    """Test suite for escalation logic and hidden evaluations."""

    def setUp(self):
        self.settings = get_settings()
        self.analyzer = SentimentAnalyzer(settings=self.settings)
        self.escalator = EscalationManager(settings=self.settings)
        TimeProvider.reset()

    def tearDown(self):
        TimeProvider.reset()

    def test_calm_high_risk_complaint_escalation(self):
        """
        Hidden evaluation: Calm high-risk complaints (e.g. account compromise)
        must escalate immediately even if customer tone is calm/neutral.
        """
        # Business hours on a Wednesday at 11:00 AM IST
        mock_time = datetime(2026, 10, 28, 11, 0, 0)
        TimeProvider.set_mock_time(mock_time)

        msg = Message(
            content="Hello. I noticed an account compromise and unauthorized access on my account. Someone may have hacked it.",
            timestamp=mock_time,
        )
        ctx = ConversationContext(started_at=mock_time)
        sentiment = self.analyzer.analyze(msg, ctx)

        # Must detect high risk
        self.assertTrue(sentiment.is_high_risk)
        self.assertIn("account compromise", sentiment.high_risk_triggers)

        record = self.escalator.check_escalation(ctx, sentiment)
        self.assertIsNotNone(record)
        self.assertEqual(record.reason, EscalationReason.HIGH_RISK_ISSUE)
        self.assertEqual(record.priority, Priority.CRITICAL)
        self.assertIn("High-risk keywords", record.activated_condition)
        self.assertTrue(len(record.conversation_summary) > 0)

    def test_duplicate_payment_and_legal_threat_escalation(self):
        """High-risk keywords for duplicate payment and legal threats."""
        mock_time = datetime(2026, 10, 28, 14, 0, 0)
        TimeProvider.set_mock_time(mock_time)

        # Duplicate payment
        msg_payment = Message(content="I see a duplicate payment on my credit card statement.")
        ctx = ConversationContext(started_at=mock_time)
        sentiment_payment = self.analyzer.analyze(msg_payment, ctx)
        self.assertTrue(sentiment_payment.is_high_risk)
        record1 = self.escalator.check_escalation(ctx, sentiment_payment)
        self.assertIsNotNone(record1)
        self.assertEqual(record1.reason, EscalationReason.HIGH_RISK_ISSUE)

        # Legal threat
        msg_legal = Message(content="If you don't refund me I will contact my lawyer for a lawsuit.")
        sentiment_legal = self.analyzer.analyze(msg_legal, ctx)
        self.assertTrue(sentiment_legal.is_high_risk)
        record2 = self.escalator.check_escalation(ctx, sentiment_legal)
        self.assertIsNotNone(record2)
        self.assertEqual(record2.reason, EscalationReason.HIGH_RISK_ISSUE)

    def test_consecutive_negative_messages_escalation(self):
        """Repeated negative messages (3+) trigger escalation."""
        mock_time = datetime(2026, 10, 28, 10, 0, 0)
        TimeProvider.set_mock_time(mock_time)
        ctx = ConversationContext(started_at=mock_time)

        # Message 1 (negative)
        m1 = Message(content="This is bad.")
        r1 = SentimentResult(sentiment=SentimentType.NEGATIVE)
        ctx.add_message(m1)
        self.assertIsNone(self.escalator.check_escalation(ctx, r1))
        ctx.sentiment_history.append(r1)

        # Message 2 (frustrated)
        m2 = Message(content="Still not working, this is frustrating.")
        r2 = SentimentResult(sentiment=SentimentType.FRUSTRATED)
        ctx.add_message(m2)
        self.assertIsNone(self.escalator.check_escalation(ctx, r2))
        ctx.sentiment_history.append(r2)

        # Message 3 (negative) -> Threshold reached
        m3 = Message(content="Terrible waste of time.")
        r3 = SentimentResult(sentiment=SentimentType.NEGATIVE)
        ctx.add_message(m3)

        record = self.escalator.check_escalation(ctx, r3)
        self.assertIsNotNone(record)
        self.assertEqual(record.reason, EscalationReason.REPEATED_NEGATIVE)
        self.assertIn("3 consecutive", record.activated_condition)

    def test_after_hours_urgent_complaint_routing(self):
        """Hidden evaluation: Urgent complaint outside business hours goes to on-call queue."""
        # 11:30 PM on Wednesday night (after hours)
        after_hours_time = datetime(2026, 10, 28, 23, 30, 0)
        TimeProvider.set_mock_time(after_hours_time)

        ctx = ConversationContext(started_at=after_hours_time)
        msg = Message(content="EMERGENCY! My server is down and production is failing right now!")
        sentiment = self.analyzer.analyze(msg, ctx)
        self.assertEqual(sentiment.sentiment, SentimentType.URGENT)

        record = self.escalator.check_escalation(ctx, sentiment)
        self.assertIsNotNone(record)
        self.assertEqual(record.reason, EscalationReason.AFTER_HOURS_URGENT)
        self.assertEqual(record.queue_type, "on_call")
        self.assertEqual(record.priority, Priority.CRITICAL)

    def test_after_hours_normal_complaint_scheduling(self):
        """Hidden evaluation: Normal complaint outside business hours scheduled for next business day."""
        # 8:00 PM on Wednesday night (after hours)
        after_hours_time = datetime(2026, 10, 28, 20, 0, 0)
        TimeProvider.set_mock_time(after_hours_time)

        ctx = ConversationContext(started_at=after_hours_time)
        msg = Message(content="I am disappointed with the delay in my regular parcel delivery.")
        sentiment = self.analyzer.analyze(msg, ctx)
        self.assertEqual(sentiment.sentiment, SentimentType.NEGATIVE)

        record = self.escalator.check_escalation(ctx, sentiment)
        self.assertIsNotNone(record)
        self.assertEqual(record.queue_type, "next_business_day")
        self.assertEqual(record.priority, Priority.MEDIUM)
        self.assertIn("next business day", record.activated_condition)

    def test_unresolved_negative_conversation_15_minutes_timeout(self):
        """Hidden evaluation: Negative conversation unresolved > 15 minutes auto-escalates."""
        # Start during business hours
        start_time = datetime(2026, 10, 28, 14, 0, 0)
        TimeProvider.set_mock_time(start_time)

        ctx = ConversationContext(started_at=start_time, is_resolved=False)
        m1 = Message(content="The item arrived damaged.", timestamp=start_time)
        r1 = SentimentResult(sentiment=SentimentType.NEGATIVE)
        ctx.add_message(m1)
        ctx.sentiment_history.append(r1)

        # 10 minutes elapsed -> No escalation yet
        TimeProvider.advance_time(minutes=10)
        curr_time = TimeProvider.now()
        m2 = Message(content="Any updates on my ticket?", timestamp=curr_time)
        r2 = SentimentResult(sentiment=SentimentType.NEUTRAL)
        self.assertIsNone(self.escalator.check_escalation(ctx, r2))

        # Advance another 6 minutes -> Total 16 minutes (> 15 minutes timeout)
        TimeProvider.advance_time(minutes=6)
        curr_time = TimeProvider.now()
        m3 = Message(content="I am still waiting here.", timestamp=curr_time)
        r3 = SentimentResult(sentiment=SentimentType.NEUTRAL)

        record = self.escalator.check_escalation(ctx, r3)
        self.assertIsNotNone(record)
        self.assertEqual(record.reason, EscalationReason.UNRESOLVED_TIMEOUT)
        self.assertIn("16.0 minutes", record.activated_condition)
        self.assertEqual(record.priority, Priority.HIGH)

    def test_simulated_time_changes_business_to_after_hours(self):
        """Hidden evaluation: Simulated time changes across business hours boundary."""
        # 17:50 - Within business hours
        t1 = datetime(2026, 10, 28, 17, 50, 0)
        TimeProvider.set_mock_time(t1)
        ctx = ConversationContext(started_at=t1)
        m1 = Message(content="Having some issues with the system.", timestamp=t1)
        r1 = SentimentResult(sentiment=SentimentType.NEGATIVE)
        ctx.add_message(m1)
        ctx.sentiment_history.append(r1)

        # Still within business hours -> Not escalated to after-hours queue
        record1 = self.escalator.check_escalation(ctx, r1)
        self.assertIsNone(record1)

        # Simulate time change: Advance to 18:15 (after-hours begins at 18:00)
        TimeProvider.advance_time(minutes=25)
        t2 = TimeProvider.now()
        m2 = Message(content="CRITICAL EMERGENCY! System completely crashed!", timestamp=t2)
        r2 = self.analyzer.analyze(m2, ctx)

        # Now outside business hours -> Routes to on-call queue
        record2 = self.escalator.check_escalation(ctx, r2)
        self.assertIsNotNone(record2)
        self.assertEqual(record2.reason, EscalationReason.AFTER_HOURS_URGENT)
        self.assertEqual(record2.queue_type, "on_call")
        self.assertEqual(record2.priority, Priority.CRITICAL)


if __name__ == "__main__":
    unittest.main()
