"""
Input Processor for Multilingual Chatbot.

Handles:
- Common spelling correction
- Transliterated inputs (e.g. Romanized Hindi)
- Multiple inquiry detection and segmentation
- Correction identification ("actually", "I meant", "correction:")
- Low confidence detection requiring customer clarification
- Multi-lingual clarification generation
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from src.core.config.settings import get_settings, LanguageConfig
from src.core.models.data_models import Message
from src.core.utils.helpers import get_logger, normalize_text
from .language_detector import LanguageDetector

logger = get_logger("multilingual.input_processor")


# Common customer typos mapped to corrected terms
_TYPO_DICT: Dict[str, str] = {
    "ordr": "order",
    "oreder": "order",
    "odrer": "order",
    "statuss": "status",
    "staus": "status",
    "refun": "refund",
    "rfund": "refund",
    "refnd": "refund",
    "cancelation": "cancellation",
    "cancle": "cancel",
    "cancled": "canceled",
    "dilevered": "delivered",
    "delivred": "delivered",
    "delivary": "delivery",
    "delivry": "delivery",
    "waranty": "warranty",
    "warenty": "warranty",
    "prodcut": "product",
    "produc": "product",
    "shippment": "shipment",
    "shiping": "shipping",
    "acount": "account",
    "accout": "account",
    "recieved": "received",
    "recive": "receive",
    "paymnt": "payment",
    "paymet": "payment",
    "plz": "please",
    "pls": "please",
    "thx": "thanks",
    "thnx": "thanks",
}

# Clarification templates per language
_CLARIFICATION_MESSAGES: Dict[str, str] = {
    "en": "I'm not quite sure I understood that correctly. Could you please rephrase or provide more details so I can help assist you?",
    "es": "No estoy seguro de haber entendido correctamente. ¿Podría reformular su solicitud o proporcionar más detalles?",
    "fr": "Je ne suis pas certain d'avoir bien compris. Pourriez-vous reformuler ou préciser votre demande ?",
    "hi": "मुझे आपकी बात पूरी तरह समझ नहीं आई। क्या आप कृपया इसे दोबारा या अधिक विस्तार से बता सकते हैं?",
}


class InputProcessor:
    """
    Processes customer text inputs, applying typo correction, multi-request splitting,
    correction detection, and confidence checking.
    """

    def __init__(
        self,
        config: Optional[LanguageConfig] = None,
        language_detector: Optional[LanguageDetector] = None,
    ) -> None:
        self.config = config or get_settings().language
        self.detector = language_detector or LanguageDetector(self.config)

    def process(self, text: str, session_id: str = "") -> Dict[str, Any]:
        """
        Process user message text and extract structured intent, requests, and flags.

        Args:
            text: Raw input string from customer
            session_id: Context identifier

        Returns:
            Dict containing:
            - cleaned_text: Typo-corrected string
            - detected_language: ISO language code
            - confidence: Detection confidence score
            - sub_requests: List of distinct sub-requests if multiple issues mentioned
            - is_correction: Boolean indicating if user is correcting earlier info
            - correction_detail: Extracted correction if present
            - needs_clarification: True if ambiguous or low confidence
            - clarification_message: Response string to request clarification
        """
        if not text or not text.strip():
            return {
                "cleaned_text": "",
                "detected_language": self.config.default_language,
                "confidence": 0.0,
                "sub_requests": [],
                "is_correction": False,
                "correction_detail": None,
                "needs_clarification": True,
                "clarification_message": self.generate_clarification("", self.config.default_language),
            }

        # 1. Spelling normalization
        corrected_text = self._correct_typos(text)

        # 2. Language Detection
        lang, confidence = self.detector.detect(corrected_text)

        # 3. Detect Corrections
        is_correction, correction_detail = self._detect_correction(corrected_text)

        # 4. Multi-request detection
        sub_requests = self._split_requests(corrected_text)

        # 5. Low Confidence / Ambiguity Check
        needs_clarification = False
        clarification_msg = ""

        # Trigger clarification if confidence is below threshold or input is extremely cryptic
        words = corrected_text.strip().split()
        if confidence < self.config.confidence_threshold or len(words) <= 1:
            # Single word inputs like "help" or "?" need clarification unless unambiguous greeting
            greetings = {"hello", "hi", "hey", "hola", "bonjour", "namaste"}
            if len(words) <= 1 and words[0].lower() not in greetings:
                needs_clarification = True
                clarification_msg = self.generate_clarification(corrected_text, lang)
            elif confidence < 0.4:
                needs_clarification = True
                clarification_msg = self.generate_clarification(corrected_text, lang)

        return {
            "cleaned_text": corrected_text,
            "detected_language": lang,
            "confidence": confidence,
            "sub_requests": sub_requests,
            "is_correction": is_correction,
            "correction_detail": correction_detail,
            "needs_clarification": needs_clarification,
            "clarification_message": clarification_msg,
        }

    def generate_clarification(self, text: str, language: str) -> str:
        """Generate clarification prompt in the specified language."""
        return _CLARIFICATION_MESSAGES.get(language, _CLARIFICATION_MESSAGES["en"])

    def _correct_typos(self, text: str) -> str:
        """Replaces common misspelled tokens with canonical terms."""
        tokens = text.split()
        corrected_tokens = []
        for token in tokens:
            # strip basic punctuation for check
            clean = re.sub(r"[^\w]", "", token).lower()
            if clean in _TYPO_DICT:
                replacement = _TYPO_DICT[clean]
                # Preserve capitalization
                if token.isupper():
                    replacement = replacement.upper()
                elif token.istitle():
                    replacement = replacement.title()
                # Restore trailing punctuation
                punct = "".join(c for c in token if not c.isalnum())
                corrected_tokens.append(f"{replacement}{punct}")
            else:
                corrected_tokens.append(token)
        return " ".join(corrected_tokens)

    def _detect_correction(self, text: str) -> Tuple[bool, Optional[str]]:
        """Identify if customer message represents a correction."""
        patterns = [
            r"\bactually\b\s*,?\s*(.*)",
            r"\bi meant\b\s*(.*)",
            r"\bcorrection\s*:\s*(.*)",
            r"\bnot\s+([^\s,]+)\s+but\s+([^\s,]+)",
            r"\bwait,?\s*(?:i made a mistake|wrong number)\b",
        ]
        for pat in patterns:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                detail = match.group(0).strip()
                return True, detail
        return False, None

    def _split_requests(self, text: str) -> List[str]:
        """
        Split compound user messages with multiple inquiries into individual request sentences.
        E.g.: "I need to track my order and also I want to change my delivery address."
        """
        split_delimiters = [
            r"\s+and\s+also\s+",
            r"\s+as\s+well\s+as\s+",
            r"\s+also\s+",
            r"\.\s+(?=[A-Z])",
            r";\s*",
        ]
        results = [text.strip()]
        for delim in split_delimiters:
            new_results = []
            for item in results:
                parts = re.split(delim, item, flags=re.IGNORECASE)
                for p in parts:
                    clean_p = p.strip()
                    if clean_p and len(clean_p) > 5:
                        new_results.append(clean_p)
            results = new_results

        return results if len(results) > 1 else [text.strip()]
