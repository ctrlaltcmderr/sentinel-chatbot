"""
Tests for Component 6: Translator and Token Preservation.

Hidden evaluations:
- Preserving names, order IDs, dates, and product codes during translation
"""

import unittest

from src.multilingual.translator import SimpleTranslator


class TestSimpleTranslator(unittest.TestCase):
    """Test phrase translation and invariant token preservation."""

    def setUp(self):
        self.translator = SimpleTranslator()

    def test_basic_phrase_translation(self):
        # English to Spanish
        es = self.translator.translate("hello, thank you", "en", "es")
        self.assertIn("hola", es.lower())
        self.assertIn("gracias", es.lower())

        # English to French
        fr = self.translator.translate("thank you", "en", "fr")
        self.assertIn("merci", fr.lower())

    def test_token_preservation_order_and_sku(self):
        """Hidden evaluation: Preserve order IDs, SKU codes, dates, and names."""
        text = "Hello John Doe, your order ORD-998877 with item SKU-CAMERA-4K will arrive on 2026-11-05."
        # Translate to Spanish
        translated = self.translator.translate(text, "en", "es")

        # Invariant tokens must remain completely intact
        self.assertIn("ORD-998877", translated)
        self.assertIn("SKU-CAMERA-4K", translated)
        self.assertIn("2026-11-05", translated)
        self.assertIn("John Doe", translated)


if __name__ == "__main__":
    unittest.main()
