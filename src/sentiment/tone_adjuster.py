"""
Tone Adjuster for Sentinel Chatbot.

Adjusts the response tone based on customer sentiment and conversation history
without altering underlying business policies, prices, refund rules, or facts.
"""

from __future__ import annotations

import re
from typing import Optional

from src.core.models.data_models import (
    ConversationContext,
    SentimentResult,
    SentimentType,
)
from src.core.utils.helpers import get_logger

logger = get_logger("sentiment.tone_adjuster")


class ToneAdjuster:
    """
    Adjusts the tone of chatbot responses according to customer sentiment
    while strictly preserving business rules, financial terms, and policy details.
    """

    # Tone prefixes and adjustments by sentiment type
    _EMPATHY_PREFIXES = {
        SentimentType.FRUSTRATED: (
            "I completely understand how frustrating this has been for you, and I appreciate your patience. "
        ),
        SentimentType.NEGATIVE: (
            "I am genuinely sorry to hear about your experience. Let me help make this right. "
        ),
        SentimentType.URGENT: (
            "I recognize the urgency of your situation and am prioritizing this immediately. "
        ),
        SentimentType.SARCASTIC: (
            "I recognize your frustration with this situation, and I appreciate you bringing it to our attention. "
            "Let's work through this systematically to get it resolved. "
        ),
        SentimentType.POSITIVE: (
            "Thank you so much for your kind words! "
        ),
        SentimentType.NEUTRAL: "",
    }

    _EMPATHY_SUFFIXES = {
        SentimentType.FRUSTRATED: (
            "\n\nI will stay with you until this issue is completely resolved."
        ),
        SentimentType.NEGATIVE: (
            "\n\nPlease let me know if there is anything else I can do to assist you."
        ),
        SentimentType.URGENT: (
            "\n\nWe are actively monitoring this request to ensure swift resolution."
        ),
        SentimentType.SARCASTIC: (
            "\n\nOur team is committed to addressing your concerns promptly and thoroughly."
        ),
        SentimentType.POSITIVE: (
            "\n\nIt was a pleasure assisting you today!"
        ),
        SentimentType.NEUTRAL: "",
    }

    # Policy and business term patterns that must NEVER be modified
    _POLICY_PATTERNS = [
        r"\$\d+(?:\.\d{2})?",
        r"\b\d+%\b",
        r"\b\d+\s*(?:day|days|business days|hours)\b",
        r"\b(?:refund|non-refundable|warranty|guarantee|replacement|charge|fee)\b",
        r"\b(?:policy|terms and conditions|clause|section)\b",
    ]

    def adjust_response(
        self,
        response: str,
        sentiment: SentimentResult,
        context: Optional[ConversationContext] = None,
    ) -> str:
        """
        Adjusts response tone based on sentiment while maintaining business policies.

        Args:
            response: Base factual response adhering to policies
            sentiment: Detected sentiment result
            context: Optional conversation context to evaluate trend

        Returns:
            Adjusted response string
        """
        if not response or not response.strip():
            return response

        # Check sentiment trend if context is available
        is_worsening = False
        if context and len(context.sentiment_history) >= 2:
            prev = context.sentiment_history[-2]
            if prev.sentiment in (SentimentType.POSITIVE, SentimentType.NEUTRAL) and \
               sentiment.sentiment in (SentimentType.NEGATIVE, SentimentType.FRUSTRATED):
                is_worsening = True

        prefix = self._EMPATHY_PREFIXES.get(sentiment.sentiment, "")
        suffix = self._EMPATHY_SUFFIXES.get(sentiment.sentiment, "")

        if is_worsening and sentiment.sentiment in (SentimentType.NEGATIVE, SentimentType.FRUSTRATED):
            prefix = "I notice this is becoming more difficult, and I apologize for the continued difficulty. "

        if sentiment.is_high_risk:
            prefix = "I understand this is a critical matter regarding your account and transaction safety. " + prefix

        # Combine ensuring clean formatting
        cleaned_response = response.strip()
        
        # Don't duplicate prefixes if already present
        if prefix and cleaned_response.lower().startswith(prefix.strip().lower()[:20]):
            adjusted = cleaned_response
        else:
            adjusted = f"{prefix}{cleaned_response}"

        if suffix and not adjusted.endswith(suffix.strip()):
            adjusted = f"{adjusted}{suffix}"

        return adjusted
