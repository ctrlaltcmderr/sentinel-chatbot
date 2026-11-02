"""
Tests for Component 1: Tone Adjuster.
"""

import unittest

from src.core.models.data_models import (
    ConversationContext,
    SentimentResult,
    SentimentType,
)
from src.sentiment.tone_adjuster import ToneAdjuster


class TestToneAdjuster(unittest.TestCase):
    """Test tone adjustment preserving business policies."""

    def setUp(self):
        self.adjuster = ToneAdjuster()

    def test_frustrated_tone_adjustment(self):
        sentiment = SentimentResult(sentiment=SentimentType.FRUSTRATED)
        base_policy_response = "Our refund policy requires items to be returned within 30 days for a full $50 refund."
        adjusted = self.adjuster.adjust_response(base_policy_response, sentiment)

        # Empathy added
        self.assertIn("frustrating", adjusted.lower())
        # Business policies untouched
        self.assertIn("30 days", adjusted)
        self.assertIn("$50", adjusted)
        self.assertIn("refund", adjusted)

    def test_urgent_tone_adjustment(self):
        sentiment = SentimentResult(sentiment=SentimentType.URGENT)
        base_response = "A technician will visit between 9 AM and 1 PM."
        adjusted = self.adjuster.adjust_response(base_response, sentiment)
        self.assertIn("urgency", adjusted.lower())
        self.assertIn("9 AM and 1 PM", adjusted)

    def test_sarcastic_tone_adjustment(self):
        sentiment = SentimentResult(sentiment=SentimentType.SARCASTIC)
        base_response = "Your replacement will arrive on Friday."
        adjusted = self.adjuster.adjust_response(base_response, sentiment)
        self.assertIn("frustration", adjusted.lower())
        self.assertIn("Friday", adjusted)

    def test_neutral_tone_unaltered(self):
        sentiment = SentimentResult(sentiment=SentimentType.NEUTRAL)
        base_response = "Store hours are Monday through Friday, 9 AM to 6 PM."
        adjusted = self.adjuster.adjust_response(base_response, sentiment)
        self.assertEqual(adjusted.strip(), base_response.strip())


if __name__ == "__main__":
    unittest.main()
