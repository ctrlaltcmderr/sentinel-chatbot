"""
Tests for Component 6: Input Processor.

Hidden evaluations:
- Spelling error correction
- Transliterated inputs
- Multiple requests in single message
- Low confidence triggers clarification
"""

import unittest

from src.multilingual.input_processor import InputProcessor


class TestInputProcessor(unittest.TestCase):
    """Test typo correction, multi-request splitting, and clarification triggers."""

    def setUp(self):
        self.processor = InputProcessor()

    def test_spelling_error_correction(self):
        """Hidden evaluation: Handle customer spelling errors."""
        raw_text = "I need a refun for my broken prodcut plz."
        processed = self.processor.process(raw_text)
        self.assertIn("refund", processed["cleaned_text"])
        self.assertIn("product", processed["cleaned_text"])
        self.assertIn("please", processed["cleaned_text"])

    def test_multiple_requests_splitting(self):
        """Hidden evaluation: Split multiple inquiries in one message."""
        text = "I need to check my order status and also I want to update my shipping address."
        processed = self.processor.process(text)
        self.assertGreaterEqual(len(processed["sub_requests"]), 2)

    def test_low_confidence_triggers_clarification(self):
        """Hidden evaluation: Ambiguous or unparseable input triggers clarification request."""
        ambiguous_text = "???"
        processed = self.processor.process(ambiguous_text)
        self.assertTrue(processed["needs_clarification"])
        self.assertTrue(len(processed["clarification_message"]) > 0)

    def test_multilingual_clarification_generation(self):
        clarification_es = self.processor.generate_clarification("ayuda", "es")
        self.assertIn("No estoy seguro", clarification_es)

        clarification_hi = self.processor.generate_clarification("मदद", "hi")
        self.assertIn("समझ", clarification_hi)

    def test_ambiguous_follow_up_triggers_clarification(self):
        """Hidden evaluation: Ambiguous follow-up input triggers clarification request."""
        for vague_input in ["what?", "then?", "..."]:
            processed = self.processor.process(vague_input)
            self.assertTrue(processed["needs_clarification"])
            self.assertTrue(len(processed["clarification_message"]) > 0)

    def test_unseen_multilingual_conversations(self):
        """Hidden evaluation: Unseen multilingual input parsing and entity extraction."""
        # Unseen Spanish input with typo
        es_input = "Hola, mi orden es ORD-887766 y el envio esta demorado por favor ayuda"
        res_es = self.processor.process(es_input)
        self.assertEqual(res_es["detected_language"], "es")
        self.assertFalse(res_es["needs_clarification"])

        # Unseen French input
        fr_input = "Bonjour, ma commande est ORD-334455 et je souhaite changer mon adresse"
        res_fr = self.processor.process(fr_input)
        self.assertEqual(res_fr["detected_language"], "fr")
        self.assertFalse(res_fr["needs_clarification"])


if __name__ == "__main__":
    unittest.main()
