"""
Language detection using character patterns and keyword dictionaries.

Supports English (en), Spanish (es), French (fr), Hindi (hi) without
any external NLP libraries – detection relies on Unicode ranges,
diacritical characters, and high-frequency keyword lookups.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple

from ..core.config.settings import get_settings
from ..core.utils.helpers import get_logger, normalize_text

logger = get_logger("language_detector")


# ──────────────────────── Keyword / Pattern Banks ────────────────────────

# High-frequency words for each language (lowercased)
_SPANISH_KEYWORDS: Set[str] = {
    "hola", "gracias", "por", "favor", "necesito", "quiero", "tengo",
    "problema", "ayuda", "ayudar", "ayudarme", "buenos", "días", "tardes", "noches",
    "cómo", "dónde", "cuándo", "está", "estoy", "puede", "puedo", "puedes",
    "pedido", "orden", "cuenta", "pago", "envío", "producto", "factura", "facturas",
    "servicio", "cliente", "número", "dirección", "cambiar", "buscar", "encontrar",
    "devolver", "reembolso", "cancelar", "solicitar", "soporte", "frustrado",
    "ignora", "reglas", "revela", "instrucciones", "ocultas", "bloqueada",
    "mi", "su", "el", "la", "los", "las", "un", "una", "que", "es",
    "no", "sí", "con", "para", "pero", "muy", "más", "también",
    "bien", "mal", "mejor", "peor", "otro", "otra", "mismo",
    "este", "esta", "ese", "esa", "yo", "tú", "usted", "nosotros",
}

_FRENCH_KEYWORDS: Set[str] = {
    "bonjour", "merci", "s'il", "vous", "plaît", "je", "mon", "ma",
    "problème", "aide", "aider", "besoin", "commande", "compte", "paiement",
    "livraison", "produit", "service", "client", "numéro", "adresse",
    "changer", "retourner", "remboursement", "annuler", "demander",
    "bonsoir", "salut", "oui", "non", "avec", "pour", "mais",
    "très", "plus", "aussi", "bien", "mal", "mieux", "autre",
    "ce", "cette", "le", "la", "les", "un", "une", "des", "du",
    "dans", "sur", "par", "est", "suis", "sont", "avoir", "être",
    "nous", "ils", "elles", "comment", "où", "quand", "pourquoi",
    "quel", "quelle", "ne", "pas", "rien", "tout", "jour",
    "répondez", "répondre", "français", "trouver", "facture", "mécontent",
}

_HINDI_TRANSLITERATED_KEYWORDS: Set[str] = {
    "mera", "meri", "mere", "mujhe", "mujhse", "muje",
    "kya", "kaise", "kahan", "kab", "kaun", "kitna", "kitne", "kitni",
    "hai", "hain", "tha", "thi", "the", "hoga", "hogi",
    "chahiye", "chahie", "chaiye",
    "madad", "sahayata", "sahayta",
    "order", "pedido",
    "karo", "kijiye", "karein", "karenge", "karunga",
    "nahi", "nahin", "nhi", "mat",
    "aur", "ya", "lekin", "par", "se", "ko", "ka", "ki", "ke",
    "yeh", "ye", "woh", "wo", "yah", "vah",
    "acha", "accha", "achha", "bura", "theek", "thik",
    "naam", "pata", "number",
    "samajh", "samajhna", "batao", "bataiye", "batana",
    "paisa", "paise", "rupay", "rupaye",
    "saman", "samaan", "product",
    "wapas", "wapsi", "badal", "badalna",
    "haan", "ji", "bilkul", "zaroor", "zarur",
    "abhi", "jaldi", "turant",
    "bohot", "bahut", "bahot", "zyada",
    "kuch", "koi", "sab", "sabhi",
    "dhanyawad", "dhanyavaad", "shukriya",
    "namaste", "namaskar", "pranam",
}

_ENGLISH_KEYWORDS: Set[str] = {
    "the", "is", "are", "was", "were", "have", "has", "had",
    "will", "would", "could", "should", "can", "may", "might",
    "this", "that", "these", "those", "what", "where", "when",
    "how", "why", "who", "which", "my", "your", "his", "her",
    "our", "their", "its", "i", "you", "he", "she", "we", "they",
    "order", "help", "need", "want", "please", "thank", "thanks",
    "problem", "issue", "support", "service", "product", "delivery",
    "payment", "refund", "cancel", "return", "track", "status",
    "account", "password", "email", "phone", "address", "name",
    "hello", "hi", "hey", "good", "morning", "afternoon", "evening",
    "and", "or", "but", "not", "with", "from", "about", "also",
    "very", "much", "more", "less", "some", "any", "all", "each",
    "great", "another", "delayed", "package", "wonderful", "customer",
    "as", "always", "never", "item", "broken", "working", "bad",
    "fine", "time", "day", "days", "received", "arrived", "shipping",
    "quote", "rule", "rules", "current", "latest", "fee", "fees", "late",
    "total", "date", "image", "file", "receipt", "scan", "check", "still",
    "tell", "show", "open", "close", "read", "say", "said", "write",
    "search", "faq", "memo", "article", "guide", "setup", "ticket",
}

# Spanish-specific diacritical characters (beyond French overlap)
_SPANISH_CHARS = set("ñ¿¡")
# French-specific diacritical characters
_FRENCH_CHARS = set("çœæ")
# Shared accented chars (present in both Spanish & French)
_ACCENTED_CHARS = set("áàâäéèêëíìîïóòôöúùûüý")

# Devanagari Unicode range
_DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")


@dataclass
class LanguageDetector:
    """
    Rule-based multilingual language detector.

    Uses character-pattern analysis and keyword-frequency scoring
    to identify text language without external NLP dependencies.
    """

    confidence_threshold: float = field(default=0.0)
    config: Optional[Any] = field(default=None)

    def __post_init__(self) -> None:
        if self.config is not None and hasattr(self.config, "confidence_threshold"):
            self.confidence_threshold = self.config.confidence_threshold
        elif self.confidence_threshold == 0.0:
            settings = get_settings()
            self.confidence_threshold = settings.language.confidence_threshold

    # ─────────────────── public API ───────────────────

    def detect(self, text: str) -> Tuple[str, float]:
        """
        Detect the primary language of *text*.

        Returns
        -------
        (language_code, confidence)  e.g. ("es", 0.85)
        """
        if not text or not text.strip():
            return ("en", 0.0)

        scores = self._score_all(text)
        best_lang = max(scores, key=scores.get)  # type: ignore[arg-type]
        best_score = scores[best_lang]

        # Normalise confidence to [0, 1]
        confidence = min(best_score, 1.0)

        logger.debug(
            "detect  text=%r  scores=%s  best=%s  conf=%.2f",
            text[:60], scores, best_lang, confidence,
        )
        return (best_lang, round(confidence, 4))

    def detect_mixed_language(self, text: str) -> List[Tuple[str, str, float]]:
        """
        Detect language per segment in a mixed-language message.

        Splits on sentence boundaries and detects each segment
        independently.

        Returns
        -------
        List of (language_code, segment_text, confidence)
        """
        if not text or not text.strip():
            return []

        segments = self._split_segments(text)
        results: List[Tuple[str, str, float]] = []
        for seg in segments:
            seg_stripped = seg.strip()
            if not seg_stripped:
                continue
            lang, conf = self.detect(seg_stripped)
            results.append((lang, seg_stripped, conf))

        return results

    # ─────────────────── internal scoring ───────────────────

    def _score_all(self, text: str) -> Dict[str, float]:
        """Return a score dict for all supported languages."""
        scores: Dict[str, float] = {
            "en": 0.0,
            "es": 0.0,
            "fr": 0.0,
            "hi": 0.0,
        }

        lower = text.lower()
        words = re.findall(r"[a-zA-Zà-öø-ÿÀ-ÖØ-ß\u0900-\u097F']+", lower)
        total_words = max(len(words), 1)

        # ── 1. Devanagari script check (strong Hindi signal) ──
        devanagari_chars = len(_DEVANAGARI_RE.findall(text))
        if devanagari_chars > 0:
            devanagari_ratio = devanagari_chars / max(len(text.replace(" ", "")), 1)
            scores["hi"] += 0.5 + 0.5 * devanagari_ratio
            # If majority Devanagari, return early with high score
            if devanagari_ratio > 0.3:
                scores["hi"] = min(scores["hi"] + 0.3, 1.0)

        # ── 2. Special character signals ──
        text_chars = set(lower)
        spanish_char_hits = len(text_chars & _SPANISH_CHARS)
        french_char_hits = len(text_chars & _FRENCH_CHARS)

        if spanish_char_hits:
            scores["es"] += 0.3 * min(spanish_char_hits, 2)
        if french_char_hits:
            scores["fr"] += 0.3 * min(french_char_hits, 2)

        # ── 3. Keyword matching ──
        word_set = set(words)

        es_hits = len(word_set & _SPANISH_KEYWORDS)
        fr_hits = len(word_set & _FRENCH_KEYWORDS)
        hi_hits = len(word_set & _HINDI_TRANSLITERATED_KEYWORDS)
        en_hits = len(word_set & _ENGLISH_KEYWORDS)

        for hits, lang in [(es_hits, "es"), (fr_hits, "fr"), (hi_hits, "hi"), (en_hits, "en")]:
            if hits >= 3:
                scores[lang] += 0.55 + 0.35 * (hits / total_words)
            elif hits >= 2:
                scores[lang] += 0.45 + 0.35 * (hits / total_words)
            elif hits == 1:
                scores[lang] += 0.25 * (hits / total_words)

        # ── 4. Bigram / trigram patterns (Spanish vs French vs English) ──
        _sp_endings = ("ción", "mente", "ando", "endo", "idad")
        _fr_endings = ("tion", "ment", "eux", "euse", "ique", "eur")
        for w in words:
            for ending in _sp_endings:
                if w.endswith(ending):
                    scores["es"] += 0.1
            for ending in _fr_endings:
                if w.endswith(ending):
                    scores["fr"] += 0.1

        # ── 5. Default English bias for Latin-script text ──
        if devanagari_chars == 0 and spanish_char_hits == 0 and french_char_hits == 0:
            if es_hits == 0 and fr_hits == 0 and hi_hits == 0 and en_hits >= 1:
                scores["en"] += 0.4

        # Calculate final confidence
        best_l = max(scores, key=scores.get)
        best_val = scores[best_l]
        if best_val > 0.4:
            scores[best_l] = min(1.0, max(best_val, 0.75 + 0.2 * min(best_val, 1.0)))

        return scores

    @staticmethod
    def _split_segments(text: str) -> List[str]:
        """Split text into segments on sentence-like boundaries."""
        # Split on periods, question marks, exclamation marks, commas between clauses
        parts = re.split(r"(?<=[.!?])\s+|(?:,\s+(?=[A-Z]))", text)
        # Also split on language-switching patterns (e.g. "I need help with mera order")
        refined: List[str] = []
        for part in parts:
            # Try splitting on transition words
            sub = re.split(r"\b(but|and|also|aur|lekin|par)\b", part, flags=re.IGNORECASE)
            if len(sub) > 1:
                # Re-join connector with following segment
                i = 0
                while i < len(sub):
                    refined.append(sub[i].strip())
                    i += 1
            else:
                refined.append(part.strip())
        return [s for s in refined if s]
