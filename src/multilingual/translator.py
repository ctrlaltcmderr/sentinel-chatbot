"""
Dictionary-based phrase translator for customer-service scenarios.

Translates common support phrases between English, Spanish, French,
and Hindi using curated dictionaries. Preserves untranslatable tokens
such as order IDs (ORD-xxx), product codes (SKU-xxx), names, and dates.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from ..core.utils.helpers import get_logger

logger = get_logger("translator")

# ───────────────────────── Phrase Dictionaries ─────────────────────────
# Keyed by (source_lang, target_lang) → { source_phrase: target_phrase }
# English is the hub language; other pairs route through English.

_PHRASE_DICTS: Dict[Tuple[str, str], Dict[str, str]] = {}


def _register(src: str, tgt: str, pairs: Dict[str, str]) -> None:
    """Register phrase pairs in both directions."""
    _PHRASE_DICTS[(src, tgt)] = {k.lower(): v for k, v in pairs.items()}
    _PHRASE_DICTS[(tgt, src)] = {v.lower(): k for k, v in pairs.items()}


# ── English ↔ Spanish ──
_register("en", "es", {
    # Greetings
    "hello": "hola",
    "hi": "hola",
    "good morning": "buenos días",
    "good afternoon": "buenas tardes",
    "good evening": "buenas noches",
    "goodbye": "adiós",
    "thank you": "gracias",
    "thanks": "gracias",
    "please": "por favor",
    "yes": "sí",
    "no": "no",
    # Common issues
    "i need help": "necesito ayuda",
    "i have a problem": "tengo un problema",
    "my order is delayed": "mi pedido está retrasado",
    "i want a refund": "quiero un reembolso",
    "i want to cancel my order": "quiero cancelar mi pedido",
    "i want to return this product": "quiero devolver este producto",
    "my payment failed": "mi pago falló",
    "i can't login": "no puedo iniciar sesión",
    "i forgot my password": "olvidé mi contraseña",
    "where is my order": "dónde está mi pedido",
    # Responses / status
    "your order has been shipped": "su pedido ha sido enviado",
    "your refund has been processed": "su reembolso ha sido procesado",
    "please wait": "por favor espere",
    "is there anything else i can help with": "¿hay algo más en lo que pueda ayudar?",
    "i understand your concern": "entiendo su preocupación",
    "let me check that for you": "déjeme verificar eso por usted",
    "your order status is": "el estado de su pedido es",
    "we apologize for the inconvenience": "pedimos disculpas por las molestias",
    "how can i help you": "¿cómo puedo ayudarte?",
    "can you provide your order id": "¿puede proporcionar su número de pedido?",
})

# ── English ↔ French ──
_register("en", "fr", {
    # Greetings
    "hello": "bonjour",
    "hi": "salut",
    "good morning": "bonjour",
    "good afternoon": "bon après-midi",
    "good evening": "bonsoir",
    "goodbye": "au revoir",
    "thank you": "merci",
    "thanks": "merci",
    "please": "s'il vous plaît",
    "yes": "oui",
    "no": "non",
    # Common issues
    "i need help": "j'ai besoin d'aide",
    "i have a problem": "j'ai un problème",
    "my order is delayed": "ma commande est en retard",
    "i want a refund": "je veux un remboursement",
    "i want to cancel my order": "je veux annuler ma commande",
    "i want to return this product": "je veux retourner ce produit",
    "my payment failed": "mon paiement a échoué",
    "i can't login": "je ne peux pas me connecter",
    "i forgot my password": "j'ai oublié mon mot de passe",
    "where is my order": "où est ma commande",
    # Responses / status
    "your order has been shipped": "votre commande a été expédiée",
    "your refund has been processed": "votre remboursement a été traité",
    "please wait": "veuillez patienter",
    "is there anything else i can help with": "y a-t-il autre chose que je puisse faire?",
    "i understand your concern": "je comprends votre préoccupation",
    "let me check that for you": "laissez-moi vérifier cela pour vous",
    "your order status is": "le statut de votre commande est",
    "we apologize for the inconvenience": "nous nous excusons pour le désagrément",
    "how can i help you": "comment puis-je vous aider?",
    "can you provide your order id": "pouvez-vous fournir votre numéro de commande?",
})

# ── English ↔ Hindi ──
_register("en", "hi", {
    # Greetings
    "hello": "namaste",
    "hi": "namaste",
    "good morning": "suprabhat",
    "good afternoon": "namaskar",
    "good evening": "shubh sandhya",
    "goodbye": "alvida",
    "thank you": "dhanyavaad",
    "thanks": "shukriya",
    "please": "kripya",
    "yes": "haan",
    "no": "nahi",
    # Common issues
    "i need help": "mujhe madad chahiye",
    "i have a problem": "meri ek samasya hai",
    "my order is delayed": "mera order late hai",
    "i want a refund": "mujhe refund chahiye",
    "i want to cancel my order": "mujhe order cancel karna hai",
    "i want to return this product": "mujhe yeh product wapas karna hai",
    "my payment failed": "mera payment fail ho gaya",
    "i can't login": "main login nahi kar pa raha",
    "i forgot my password": "main apna password bhool gaya",
    "where is my order": "mera order kahan hai",
    # Responses / status
    "your order has been shipped": "aapka order bhej diya gaya hai",
    "your refund has been processed": "aapka refund process ho gaya hai",
    "please wait": "kripya pratiksha karein",
    "is there anything else i can help with": "kya aur kuch madad chahiye?",
    "i understand your concern": "main aapki chinta samajhta hoon",
    "let me check that for you": "main aapke liye check karta hoon",
    "your order status is": "aapke order ka status hai",
    "we apologize for the inconvenience": "asuvida ke liye kshama karein",
    "how can i help you": "main aapki kaise madad kar sakta hoon?",
    "can you provide your order id": "kya aap apna order id de sakte hain?",
})

# Token-preservation regex patterns
_TOKEN_PATTERNS: List[Tuple[str, re.Pattern[str]]] = [
    ("ORDER_ID", re.compile(r"\bORD-[A-Za-z0-9]+\b", re.IGNORECASE)),
    ("SKU", re.compile(r"\bSKU-[A-Za-z0-9]+\b", re.IGNORECASE)),
    ("DATE_ISO", re.compile(r"\b\d{4}-\d{2}-\d{2}\b")),
    ("DATE_SLASH", re.compile(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b")),
    ("EMAIL", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    ("PHONE", re.compile(r"(?:\+\d{1,3}[-\s]?)?\(?\d{3}\)?[-\s]?\d{3}[-\s]?\d{4}")),
    ("AMOUNT", re.compile(r"[\$€£₹]\s*\d+(?:[.,]\d{1,2})?")),
    ("PROPER_NAME", re.compile(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b")),
]


@dataclass
class SimpleTranslator:
    """
    Dictionary-based phrase translator.

    Translates known customer-service phrases between supported
    language pairs while preserving special tokens (order IDs,
    product codes, dates, names).
    """

    supported_pairs: set = field(default_factory=lambda: set(_PHRASE_DICTS.keys()))

    # ─────────────────── public API ───────────────────

    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        """
        Translate *text* from *source_lang* to *target_lang*.

        Falls back to the original text for untranslatable segments.
        Routes through English hub when no direct dictionary exists.
        """
        if source_lang == target_lang:
            return text

        # Preserve tokens
        safe_text, token_map = self.preserve_tokens(text)

        translated = self._translate_text(safe_text, source_lang, target_lang)

        # Restore tokens
        result = self.restore_tokens(translated, token_map)
        logger.debug(
            "translate  src=%s  tgt=%s  in=%r  out=%r",
            source_lang, target_lang, text[:60], result[:60],
        )
        return result

    def preserve_tokens(self, text: str) -> Tuple[str, Dict[str, str]]:
        """
        Replace special tokens with placeholders.

        Returns (modified_text, {placeholder: original_token}).
        """
        token_map: Dict[str, str] = {}
        result = text
        counter = 0

        for tag, pattern in _TOKEN_PATTERNS:
            for match in pattern.finditer(result):
                original = match.group(0)
                placeholder = f"__{tag}_{counter}__"
                token_map[placeholder] = original
                counter += 1

        # Apply replacements (reverse order to preserve positions)
        for placeholder, original in sorted(
            token_map.items(), key=lambda x: result.find(x[1]), reverse=True
        ):
            result = result.replace(original, placeholder, 1)

        return result, token_map

    def restore_tokens(self, text: str, tokens: Dict[str, str]) -> str:
        """Restore preserved tokens from placeholders."""
        result = text
        for placeholder, original in tokens.items():
            result = result.replace(placeholder, original)
        return result

    # ─────────────────── internal ───────────────────

    def _translate_text(self, text: str, src: str, tgt: str) -> str:
        """Attempt phrase-level translation; fall back to word-level."""
        pair = (src, tgt)

        # Try direct pair
        if pair in _PHRASE_DICTS:
            return self._apply_dictionary(text, _PHRASE_DICTS[pair])

        # Route through English hub
        if src != "en" and tgt != "en":
            pair_to_en = (src, "en")
            pair_from_en = ("en", tgt)
            if pair_to_en in _PHRASE_DICTS and pair_from_en in _PHRASE_DICTS:
                intermediate = self._apply_dictionary(
                    text, _PHRASE_DICTS[pair_to_en]
                )
                return self._apply_dictionary(
                    intermediate, _PHRASE_DICTS[pair_from_en]
                )

        # No dictionary available – return original
        logger.warning(
            "No translation dictionary for %s → %s; returning original", src, tgt
        )
        return text

    @staticmethod
    def _apply_dictionary(text: str, dictionary: Dict[str, str]) -> str:
        """
        Apply dictionary translations, longest-match first.

        Preserves original casing style when possible.
        """
        lower_text = text.lower()
        result = text

        # Sort keys longest-first so multi-word phrases match before sub-phrases
        sorted_keys = sorted(dictionary.keys(), key=len, reverse=True)

        for src_phrase in sorted_keys:
            idx = lower_text.find(src_phrase)
            if idx != -1:
                tgt_phrase = dictionary[src_phrase]
                # Match casing of original
                original_segment = result[idx : idx + len(src_phrase)]
                if original_segment.isupper():
                    replacement = tgt_phrase.upper()
                elif original_segment[0].isupper():
                    replacement = tgt_phrase[0].upper() + tgt_phrase[1:]
                else:
                    replacement = tgt_phrase

                result = result[:idx] + replacement + result[idx + len(src_phrase):]
                lower_text = result.lower()

        return result
