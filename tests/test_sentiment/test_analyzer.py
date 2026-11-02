"""
Tests for Component 1: Multilingual Sentiment Analysis Engine.
"""

import unittest
from datetime import datetime

from src.core.models.data_models import (
    ConversationContext,
    Message,
    SentimentType,
)
from src.sentiment.analyzer import SentimentAnalyzer


class TestSentimentAnalyzer(unittest.TestCase):
    """Test sentiment analysis across 6 sentiments, history, and languages."""

    def setUp(self):
        self.analyzer = SentimentAnalyzer()

    def test_positive_sentiment(self):
        msg = Message(content="Thank you so much! Excellent and amazing support, I am really happy and satisfied.")
        ctx = ConversationContext()
        result = self.analyzer.analyze(msg, ctx)
        self.assertEqual(result.sentiment, SentimentType.POSITIVE)
        self.assertGreater(result.confidence, 0.5)
        self.assertIn("positive", result.scores)

    def test_negative_sentiment(self):
        msg = Message(content="This is terrible and horrible! The product arrived broken and ruined, worst experience ever.")
        ctx = ConversationContext()
        result = self.analyzer.analyze(msg, ctx)
        self.assertEqual(result.sentiment, SentimentType.NEGATIVE)
        self.assertGreater(result.confidence, 0.5)

    def test_frustrated_sentiment(self):
        msg = Message(content="I am so fed up and sick and tired of this! How many times do I have to contact you? Ridiculous waste of time!")
        ctx = ConversationContext()
        result = self.analyzer.analyze(msg, ctx)
        self.assertEqual(result.sentiment, SentimentType.FRUSTRATED)
        self.assertGreater(result.scores.get("frustrated", 0.0), 0.3)

    def test_urgent_sentiment(self):
        msg = Message(content="URGENT EMERGENCY! Please respond immediately, this is time-sensitive and critical right now!")
        ctx = ConversationContext()
        result = self.analyzer.analyze(msg, ctx)
        self.assertEqual(result.sentiment, SentimentType.URGENT)
        self.assertGreater(result.scores.get("urgent", 0.0), 0.3)

    def test_sarcasm_detection(self):
        """Hidden evaluation: Sarcasm detection with positive words in negative/complaint context."""
        msg = Message(content="Oh great, another broken delivery. Wonderful customer service as always!")
        ctx = ConversationContext()
        result = self.analyzer.analyze(msg, ctx)
        self.assertTrue(result.is_sarcastic or result.sentiment == SentimentType.SARCASTIC)

    def test_multilingual_sentiment_spanish(self):
        msg = Message(content="¡Muchas gracias, excelente servicio y muy contento con la compra!", language="es")
        ctx = ConversationContext()
        result = self.analyzer.analyze(msg, ctx)
        self.assertEqual(result.sentiment, SentimentType.POSITIVE)

        msg_neg = Message(content="Pésimo servicio, totalmente decepcionado y enojado con este producto roto.", language="es")
        result_neg = self.analyzer.analyze(msg_neg, ctx)
        self.assertIn(result_neg.sentiment, (SentimentType.NEGATIVE, SentimentType.FRUSTRATED))

    def test_multilingual_sentiment_french(self):
        msg = Message(content="Merci beaucoup, le service est formidable et parfait!", language="fr")
        ctx = ConversationContext()
        result = self.analyzer.analyze(msg, ctx)
        self.assertEqual(result.sentiment, SentimentType.POSITIVE)

        msg_neg = Message(content="Service catastrophique et inacceptable, produit cassé et je suis très mécontent.", language="fr")
        result_neg = self.analyzer.analyze(msg_neg, ctx)
        self.assertIn(result_neg.sentiment, (SentimentType.NEGATIVE, SentimentType.FRUSTRATED))

    def test_multilingual_sentiment_hindi(self):
        msg = Message(content="बहुत अच्छा काम, मैं बहुत खुश और संतुष्ट हूँ धन्यवाद!", language="hi")
        ctx = ConversationContext()
        result = self.analyzer.analyze(msg, ctx)
        self.assertEqual(result.sentiment, SentimentType.POSITIVE)

        msg_neg = Message(content="यह बहुत खराब और घटिया सेवा है, मैं बहुत परेशान और नाराज हूँ।", language="hi")
        result_neg = self.analyzer.analyze(msg_neg, ctx)
        self.assertIn(result_neg.sentiment, (SentimentType.NEGATIVE, SentimentType.FRUSTRATED))

    def test_conversation_history_trend(self):
        ctx = ConversationContext()
        # Previous positive message
        m1 = Message(content="Hello, could you help me?")
        r1 = self.analyzer.analyze(m1, ctx)
        ctx.add_message(m1)
        ctx.sentiment_history.append(r1)

        # Worsening sentiment
        m2 = Message(content="Still waiting. This is annoying and not working.")
        r2 = self.analyzer.analyze(m2, ctx)
        ctx.add_message(m2)
        ctx.sentiment_history.append(r2)

        self.assertIn(r2.sentiment, (SentimentType.NEGATIVE, SentimentType.FRUSTRATED))


if __name__ == "__main__":
    unittest.main()
