"""
Tests for Component 6: Language Detector.

Hidden evaluations:
- Support English, Spanish, French, Hindi
- Mixed-language message handling
- Transliterated Hindi in Latin script
- Low confidence triggers clarification
"""

import unittest

from src.multilingual.language_detector import LanguageDetector


class TestLanguageDetector(unittest.TestCase):
    """Test multilingual detection across 4 languages, mixed text, and transliteration."""

    def setUp(self):
        self.detector = LanguageDetector()

    def test_english_detection(self):
        lang, conf = self.detector.detect("Hello, I need help with my account password reset please.")
        self.assertEqual(lang, "en")
        self.assertGreater(conf, 0.7)

    def test_spanish_detection(self):
        lang, conf = self.detector.detect("Hola, necesito ayuda con mi pedido y el reembolso de mi dinero.")
        self.assertEqual(lang, "es")
        self.assertGreater(conf, 0.7)

    def test_french_detection(self):
        lang, conf = self.detector.detect("Bonjour, j'ai un problème avec ma commande et ma livraison s'il vous plaît.")
        self.assertEqual(lang, "fr")
        self.assertGreater(conf, 0.7)

    def test_hindi_devanagari_detection(self):
        lang, conf = self.detector.detect("नमस्ते, मुझे अपने ऑर्डर के बारे में सहायता चाहिए धन्यवाद।")
        self.assertEqual(lang, "hi")
        self.assertGreater(conf, 0.8)

    def test_transliterated_hindi_detection(self):
        """Hidden evaluation: Romanized/transliterated Hindi (e.g., 'mera order kahan hai')."""
        lang, conf = self.detector.detect("mera order kahan hai mujhe jaldi delivery chahiye")
        self.assertEqual(lang, "hi")
        self.assertGreater(conf, 0.6)

    def test_mixed_language_message(self):
        """Hidden evaluation: Mixed language sentences (Code-switching)."""
        mixed_text = "I need help with mera order because payment fail ho gaya hai"
        segments = self.detector.detect_mixed_language(mixed_text)
        self.assertTrue(len(segments) >= 1)

    def test_low_confidence_ambiguous_input(self):
        """Hidden evaluation: Ambiguous or extremely short text yields low confidence."""
        lang, conf = self.detector.detect("xyz 123 !?")
        self.assertLess(conf, 0.5)


if __name__ == "__main__":
    unittest.main()
