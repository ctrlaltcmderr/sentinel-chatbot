"""
Multilingual Sentiment Analysis Engine.

Detects sentiment types (positive, neutral, negative, frustrated, urgent, sarcastic)
using keyword/pattern matching and scoring rules across multiple languages.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

from src.core.config.settings import get_settings, Settings
from src.core.models.data_models import (
    Message,
    ConversationContext,
    SentimentResult,
    SentimentType,
)
from src.core.utils.helpers import get_logger, measure_latency, normalize_text


logger = get_logger("sentiment.analyzer")


# ──────────────────────────── Keyword Dictionaries ────────────────────────────

# Each dictionary maps a language code to a list of keywords/phrases.
# Scores are applied per-match and then normalized.

POSITIVE_KEYWORDS: Dict[str, List[str]] = {
    "en": [
        "thank you", "thanks", "great", "excellent", "amazing", "awesome",
        "wonderful", "perfect", "love", "appreciate", "helpful", "good",
        "happy", "satisfied", "pleased", "fantastic", "brilliant", "nice",
        "well done", "superb", "impressed", "glad", "delighted", "outstanding",
    ],
    "es": [
        "gracias", "excelente", "maravilloso", "perfecto", "genial",
        "bueno", "bien", "encanta", "increíble", "fantástico",
        "agradecido", "contento", "feliz", "satisfecho", "estupendo",
    ],
    "fr": [
        "merci", "excellent", "merveilleux", "parfait", "génial",
        "bon", "bien", "super", "fantastique", "formidable",
        "satisfait", "content", "heureux", "magnifique", "bravo",
    ],
    "hi": [
        "धन्यवाद", "शुक्रिया", "बहुत अच्छा", "शानदार", "उत्कृष्ट",
        "अद्भुत", "बढ़िया", "खुश", "संतुष्ट", "प्रसन्न",
        "अच्छा", "सुंदर", "मज़ा", "धन्यवाद",
    ],
}

NEGATIVE_KEYWORDS: Dict[str, List[str]] = {
    "en": [
        "terrible", "awful", "horrible", "worst", "bad", "hate",
        "disappointed", "disappointing", "unacceptable", "poor",
        "useless", "waste", "broken", "defective", "ruined",
        "pathetic", "disgraceful", "dreadful", "lousy", "miserable",
        "unhappy", "dissatisfied", "annoyed", "angry", "upset",
        "not working", "doesn't work", "didn't work", "never works",
        "failed", "failure", "problem", "issue", "wrong",
        "not satisfied", "not happy", "regret",
    ],
    "es": [
        "terrible", "horrible", "peor", "malo", "odio",
        "decepcionado", "inaceptable", "inútil", "roto",
        "pésimo", "desastroso", "enojado", "furioso",
        "no funciona", "problema", "error", "fallo",
        "insatisfecho", "molesto", "triste",
    ],
    "fr": [
        "terrible", "horrible", "pire", "mauvais", "déteste",
        "déçu", "inacceptable", "inutile", "cassé",
        "lamentable", "catastrophique", "fâché", "furieux",
        "ne fonctionne pas", "problème", "erreur", "échec",
        "mécontent", "insatisfait", "ennuyé",
    ],
    "hi": [
        "भयानक", "बुरा", "खराब", "घटिया", "बेकार",
        "निराश", "असंतुष्ट", "नाराज", "गुस्सा",
        "काम नहीं करता", "समस्या", "गलत", "टूटा",
        "परेशान", "दुखी", "निराशाजनक",
    ],
}

FRUSTRATED_KEYWORDS: Dict[str, List[str]] = {
    "en": [
        "frustrated", "frustrating", "sick and tired", "fed up",
        "enough", "ridiculous", "absurd", "can't believe",
        "how many times", "again and again", "over and over",
        "still not", "yet again", "another time", "keeps happening",
        "this is the third", "this is the fourth", "waited hours",
        "waited days", "no response", "nobody cares", "give up",
        "waste of time", "tired of", "sick of", "done with",
        "unbelievable", "outrageous", "insane",
    ],
    "es": [
        "frustrado", "harto", "cansado", "ridículo", "absurdo",
        "otra vez", "de nuevo", "no puedo creer", "increíble",
        "indignante", "ya basta",
    ],
    "fr": [
        "frustré", "marre", "fatigué", "ridicule", "absurde",
        "encore une fois", "je n'en peux plus", "incroyable",
        "scandaleux", "ça suffit",
    ],
    "hi": [
        "परेशान", "तंग", "थक गया", "बेतुका", "फिर से",
        "बार बार", "हद है", "बकवास",
    ],
}

URGENT_KEYWORDS: Dict[str, List[str]] = {
    "en": [
        "urgent", "emergency", "immediately", "asap", "right now",
        "critical", "time-sensitive", "deadline", "can't wait",
        "need help now", "please hurry", "right away", "crucial",
        "as soon as possible", "help me now", "today", "now",
        "life or death", "very important", "need this today",
    ],
    "es": [
        "urgente", "emergencia", "inmediatamente", "ahora mismo",
        "crítico", "ayuda ahora", "lo antes posible", "ya",
    ],
    "fr": [
        "urgent", "urgence", "immédiatement", "tout de suite",
        "critique", "aide maintenant", "dès que possible", "vite",
    ],
    "hi": [
        "तुरंत", "आपातकालीन", "अभी", "जल्दी",
        "गंभीर", "मदद चाहिए", "फौरन",
    ],
}

# Sarcasm is primarily English; we include some Spanish/French patterns too.
SARCASTIC_PHRASES: Dict[str, List[str]] = {
    "en": [
        "oh great", "oh wonderful", "how wonderful", "how lovely",
        "thanks a lot", "thanks for nothing", "wonderful service",
        "great job", "brilliant work", "what a surprise",
        "oh really", "yeah right", "sure thing", "oh fantastic",
        "just wonderful", "just great", "just perfect",
        "exactly what i needed", "oh how nice", "lovely",
        "wow amazing", "so helpful", "truly impressive",
        "couldn't be better", "what a joy",
    ],
    "es": [
        "oh genial", "qué maravilla", "muchas gracias por nada",
        "increíble servicio", "qué sorpresa",
    ],
    "fr": [
        "oh génial", "quelle merveille", "merci pour rien",
        "quel service", "quelle surprise",
    ],
    "hi": [
        "वाह क्या बात है", "बहुत बढ़िया", "शानदार सेवा",
    ],
}

# ──────────────────────── High-Risk Patterns by Category ────────────────────────
_RISK_PATTERNS: Dict[str, List[str]] = {
    "account_compromise": [
        r"\b(?:someone|somebody|anyone)\s+(?:else\s+)?(?:has\s+)?(?:accessed|logged(?:\s+in(?:to)?)?|hacked|used|entered|compromised)\s+(?:my|the)\s+account\b",
        r"\baccess(?:ed)?\s+(?:my\s+|the\s+)?account\s+without\s+(?:my\s+)?permission\b",
        r"\bwithout\s+(?:my\s+)?permission\b",
        r"\bunauthorized\s+access\b",
        r"\baccount\s+(?:was\s+|is\s+|got\s+)?compromise(?:d)?\b",
        r"\bcompromised\s+account\b",
        r"\bhack(?:ed)?\b",
        r"\baccount\s+takeover\b",
        r"\bstolen\s+(?:credentials|password|login)\b",
        r"\bsuspicious\s+(?:login|activity)\b",
        r"\bunrecognized\s+login\b",
        r"\bsecurity\s+breach\b",
        r"\bidentity\s+theft\b",
    ],
    "unauthorized_payment": [
        r"\bunauthorized\s+(?:payment|charge|transaction|withdrawal|debit|purchase)\b",
        r"\b(?:didn't|did\s+not|never)\s+authorize\s+(?:this|the|a)\s+(?:payment|charge|transaction|purchase)\b",
        r"\bfraud(?:ulent)?\s+(?:payment|charge|transaction|activity)\b",
        r"\bstolen\s+(?:card|credit\s+card|debit\s+card)\b",
        r"\bcard\s+(?:was\s+)?stolen\b",
        r"\bsomeone\s+(?:used|charged)\s+my\s+(?:card|credit\s+card|account)\b",
    ],
    "duplicate_payment": [
        r"\bduplicate\s+(?:payment|charge|transaction|billing)\b",
        r"\bdouble\s+charg(?:e|ed|ing)\b",
        r"\bcharg(?:ed|e)\s+twice\b",
        r"\bcharg(?:ed|e)\s+double\b",
        r"\bpaid\s+twice\b",
        r"\bbilled\s+twice\b",
        r"\btwo\s+charges\s+for\s+(?:the\s+same|one)\b",
    ],
    "legal_threat": [
        r"\blegal\s+(?:action|counsel|proceedings|recourse)\b",
        r"\b(?:call|hire|contact|get)\s+(?:a\s+|my\s+)?(?:lawyer|attorney)\b",
        r"\blawsuit\b",
        r"\bsue\s+(?:you|your\s+company|the\s+company)\b",
        r"\bsuing\b",
        r"\btake\s+(?:you|this)\s+to\s+court\b",
        r"\breport\s+(?:you\s+)?to\s+(?:authorities|ftc|police|regulator)\b",
    ],
}


class SentimentAnalyzer:
    """
    Multilingual sentiment analyzer using keyword/pattern matching and scoring.

    Detects 6 sentiment types: positive, neutral, negative, frustrated,
    urgent, and sarcastic. Generates confidence scores for each type,
    analyses conversation trends, and recommends response tones.
    """

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        self.config = self.settings.sentiment

    # ────────────────── Public API ──────────────────

    @measure_latency
    def analyze(
        self, message: Message, context: ConversationContext
    ) -> SentimentResult:
        """
        Analyse a single message within its conversation context.

        Returns a SentimentResult with the dominant sentiment, confidence
        scores for every type, high-risk flags, sarcasm detection,
        and a recommended response tone.
        """
        text = message.content
        lang = message.language or context.current_language or "en"

        # 1. Score each sentiment dimension
        scores = self._compute_scores(text, lang)

        # 2. Detect sarcasm (may flip positive → sarcastic)
        is_sarcastic = self._detect_sarcasm(text, lang)
        if is_sarcastic:
            # Boost sarcastic score; reduce positive score
            scores["sarcastic"] += 0.35
            scores["positive"] = max(0.0, scores["positive"] - 0.3)

        # 3. Detect high-risk keywords and categories
        is_high_risk, high_risk_triggers, risk_category, risk_level = self._detect_high_risk(text)

        # 4. Normalise scores so they sum to ~1.0
        scores = self._normalise_scores(scores)

        # 5. Determine dominant sentiment
        dominant = max(scores, key=scores.get)  # type: ignore[arg-type]
        dominant_type = SentimentType(dominant)
        confidence = scores[dominant]

        # 6. Conversation trend analysis
        trend_note = self._analyze_trend(context)

        # 7. Recommended tone
        recommended_tone = self._recommend_tone(
            dominant_type, is_sarcastic, is_high_risk, context
        )

        result = SentimentResult(
            sentiment=dominant_type,
            confidence=confidence,
            scores=scores,
            language=lang,
            is_high_risk=is_high_risk,
            high_risk_triggers=high_risk_triggers,
            risk_category=risk_category,
            risk_level=risk_level,
            is_sarcastic=is_sarcastic,
            recommended_tone=recommended_tone,
            raw_text=text,
            analysis_notes=trend_note,
        )

        logger.info(
            "Sentiment=%s  confidence=%.2f  sarcastic=%s  high_risk=%s  lang=%s",
            dominant_type.value, confidence, is_sarcastic, is_high_risk, lang,
        )
        return result

    # ────────────────── Score Computation ──────────────────

    def _compute_scores(self, text: str, lang: str) -> Dict[str, float]:
        """Compute raw scores for each sentiment dimension."""
        lower = text.lower()
        scores: Dict[str, float] = {
            "positive": 0.0,
            "neutral": 0.1,  # small baseline so neutral wins on empty input
            "negative": 0.0,
            "frustrated": 0.0,
            "urgent": 0.0,
            "sarcastic": 0.0,
        }

        # Keyword matching
        scores["positive"] += self._keyword_score(lower, POSITIVE_KEYWORDS, lang)
        scores["negative"] += self._keyword_score(lower, NEGATIVE_KEYWORDS, lang)
        scores["frustrated"] += self._keyword_score(lower, FRUSTRATED_KEYWORDS, lang)
        scores["urgent"] += self._keyword_score(lower, URGENT_KEYWORDS, lang)
        scores["sarcastic"] += self._keyword_score(lower, SARCASTIC_PHRASES, lang)

        # Punctuation-based boosting
        exclamation_count = text.count("!")
        question_count = text.count("?")
        caps_ratio = self._caps_ratio(text)

        if exclamation_count >= 3:
            scores["frustrated"] += 0.15
            scores["urgent"] += 0.05
        if question_count >= 3:
            scores["frustrated"] += 0.10
        if caps_ratio > 0.5 and len(text) > 10:
            # Lots of caps → likely angry/frustrated
            scores["frustrated"] += 0.15
            scores["negative"] += 0.10

        # Negative intensifiers
        intensifiers = ["very", "extremely", "absolutely", "completely", "totally",
                        "utterly", "so", "really"]
        for intensifier in intensifiers:
            if intensifier in lower:
                # Amplify the dominant negative/frustrated if present
                if scores["negative"] > 0:
                    scores["negative"] += 0.05
                if scores["frustrated"] > 0:
                    scores["frustrated"] += 0.05

        # Critical risk influences urgent and negative sentiment dimensions
        for cat, patterns in _RISK_PATTERNS.items():
            for pat in patterns:
                if re.search(pat, lower):
                    if cat in {"account_compromise", "unauthorized_payment"}:
                        scores["urgent"] += 0.45
                        scores["negative"] += 0.25
                        scores["neutral"] = 0.0
                    elif cat == "duplicate_payment":
                        scores["urgent"] += 0.30
                        scores["negative"] += 0.20
                        scores["neutral"] = 0.0
                    elif cat == "legal_threat":
                        scores["negative"] += 0.40
                        scores["urgent"] += 0.25
                        scores["neutral"] = 0.0
                    break

        return scores

    def _keyword_score(
        self,
        text: str,
        keyword_dict: Dict[str, List[str]],
        lang: str,
    ) -> float:
        """Score text against a keyword dictionary for the given language."""
        score = 0.0
        keywords = keyword_dict.get(lang, [])
        # Also check English keywords as fallback (many multilingual users mix English)
        en_keywords = keyword_dict.get("en", []) if lang != "en" else []

        for kw in keywords:
            if kw in text:
                score += 0.15
        for kw in en_keywords:
            if kw in text:
                score += 0.08  # Lower weight for non-primary language match

        return score

    @staticmethod
    def _caps_ratio(text: str) -> float:
        """Return the ratio of uppercase letters in text."""
        alpha_chars = [c for c in text if c.isalpha()]
        if not alpha_chars:
            return 0.0
        upper = sum(1 for c in alpha_chars if c.isupper())
        return upper / len(alpha_chars)

    # ────────────────── Sarcasm Detection ──────────────────

    def _detect_sarcasm(self, text: str, lang: str) -> bool:
        """
        Detect sarcasm through multiple heuristics:
        1. Known sarcastic phrases from config + built-in list
        2. Positive words in negative context
        3. Excessive punctuation with complaints
        4. ALL CAPS with positive words
        """
        lower = text.lower()

        # 1. Check config sarcasm indicators
        for indicator in self.config.sarcasm_indicators:
            if indicator.lower() in lower:
                return True

        # 2. Check built-in sarcastic phrases
        phrases = SARCASTIC_PHRASES.get(lang, []) + SARCASTIC_PHRASES.get("en", [])
        for phrase in phrases:
            if phrase in lower:
                return True

        # 3. Positive words in negative context
        has_positive = any(
            kw in lower for kw in POSITIVE_KEYWORDS.get(lang, [])
        )
        has_negative = any(
            kw in lower for kw in NEGATIVE_KEYWORDS.get(lang, [])
        )
        if has_positive and has_negative:
            # Context check: if negative words dominate, it's sarcasm
            pos_count = sum(1 for kw in POSITIVE_KEYWORDS.get(lang, []) if kw in lower)
            neg_count = sum(1 for kw in NEGATIVE_KEYWORDS.get(lang, []) if kw in lower)
            if neg_count > pos_count:
                return True

        # 4. Excessive punctuation patterns
        has_excessive_punctuation = bool(
            re.search(r"[!]{3,}", text) or re.search(r"[?]{3,}", text)
        )
        if has_excessive_punctuation and has_positive:
            return True

        # 5. CAPS with complaints (positive words in caps + negative context)
        caps_words = re.findall(r"\b[A-Z]{3,}\b", text)
        if caps_words:
            caps_text = " ".join(w.lower() for w in caps_words)
            caps_positive = any(
                kw in caps_text for kw in POSITIVE_KEYWORDS.get("en", [])
            )
            if caps_positive and has_negative:
                return True

        return False

    # ────────────────── High-Risk Detection ──────────────────

    def _detect_high_risk(self, text: str) -> Tuple[bool, List[str], Optional[str], str]:
        """
        Detect high-risk triggers, risk category, and risk level.
        Runs on every customer message independently of sentiment score.
        Returns: (is_high_risk, triggers, primary_risk_category, risk_level)
        """
        lower = text.lower()
        triggers: List[str] = []
        matched_categories: List[str] = []

        # 1. Match categorized regex patterns
        for category, patterns in _RISK_PATTERNS.items():
            for pat in patterns:
                m = re.search(pat, lower)
                if m:
                    matched_str = m.group(0)
                    if matched_str not in triggers:
                        triggers.append(matched_str)
                    if category not in matched_categories:
                        matched_categories.append(category)

        # 2. Check config high-risk keywords for backwards compatibility
        for keyword in self.config.high_risk_keywords:
            if keyword.lower() in lower and keyword.lower() not in triggers:
                triggers.append(keyword.lower())
                kw = keyword.lower()
                if any(w in kw for w in ["compromise", "hacked", "unauthorized access", "permission"]):
                    if "account_compromise" not in matched_categories:
                        matched_categories.append("account_compromise")
                elif any(w in kw for w in ["unauthorized payment", "unauthorized charge", "fraud"]):
                    if "unauthorized_payment" not in matched_categories:
                        matched_categories.append("unauthorized_payment")
                elif any(w in kw for w in ["duplicate payment", "double charged", "charged twice"]):
                    if "duplicate_payment" not in matched_categories:
                        matched_categories.append("duplicate_payment")
                elif any(w in kw for w in ["legal", "lawyer", "lawsuit", "sue", "court", "attorney"]):
                    if "legal_threat" not in matched_categories:
                        matched_categories.append("legal_threat")

        is_high_risk = len(triggers) > 0
        primary_category = matched_categories[0] if matched_categories else None

        if primary_category in {"account_compromise", "unauthorized_payment", "legal_threat"}:
            risk_level = "critical"
        elif primary_category == "duplicate_payment":
            risk_level = "high"
        elif is_high_risk:
            risk_level = "high"
        else:
            risk_level = "none"

        return is_high_risk, triggers, primary_category, risk_level

    # ────────────────── Score Normalisation ──────────────────

    @staticmethod
    def _normalise_scores(scores: Dict[str, float]) -> Dict[str, float]:
        """Normalise scores so they sum to approximately 1.0."""
        total = sum(scores.values())
        if total <= 0:
            # Default to neutral
            return {k: (1.0 if k == "neutral" else 0.0) for k in scores}
        return {k: round(v / total, 4) for k, v in scores.items()}

    # ────────────────── Conversation Trend Analysis ──────────────────

    def _analyze_trend(self, context: ConversationContext) -> str:
        """Analyse sentiment trend across conversation history."""
        history = context.sentiment_history
        if len(history) < 2:
            return ""

        # Map sentiments to a numeric scale for trend detection
        sentiment_values = {
            SentimentType.POSITIVE: 2,
            SentimentType.NEUTRAL: 1,
            SentimentType.NEGATIVE: -1,
            SentimentType.FRUSTRATED: -2,
            SentimentType.URGENT: -1,
            SentimentType.SARCASTIC: -1,
        }

        recent = history[-3:]  # last 3 sentiments
        values = [sentiment_values.get(s.sentiment, 0) for s in recent]

        # Detect worsening trend
        if len(values) >= 2:
            is_worsening = all(
                values[i] >= values[i + 1] for i in range(len(values) - 1)
            ) and values[-1] < values[0]
            if is_worsening:
                return "TREND: Sentiment is worsening over recent messages."

        # Detect consecutive negative
        negative_types = {
            SentimentType.NEGATIVE,
            SentimentType.FRUSTRATED,
            SentimentType.URGENT,
        }
        consecutive_neg = sum(
            1 for s in recent if s.sentiment in negative_types
        )
        if consecutive_neg >= 2:
            return "TREND: Multiple negative sentiments detected in recent history."

        return ""

    # ────────────────── Tone Recommendation ──────────────────

    def _recommend_tone(
        self,
        sentiment: SentimentType,
        is_sarcastic: bool,
        is_high_risk: bool,
        context: ConversationContext,
    ) -> str:
        """Recommend response tone based on sentiment analysis."""
        if is_high_risk:
            return "urgent"
        if sentiment == SentimentType.URGENT:
            return "urgent"
        if sentiment == SentimentType.FRUSTRATED:
            return "empathetic"
        if sentiment == SentimentType.NEGATIVE:
            return "apologetic"
        if is_sarcastic:
            return "professional"
        if sentiment == SentimentType.POSITIVE:
            return "professional"
        return "professional"
