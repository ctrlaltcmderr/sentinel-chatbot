"""
Sentinel Chatbot - Multilingual Sentiment Analysis Engine.

Provides sentiment analysis, escalation management, and tone adjustment
for customer support conversations.
"""

from .analyzer import SentimentAnalyzer
from .escalation import EscalationManager
from .tone_adjuster import ToneAdjuster

__all__ = [
    "SentimentAnalyzer",
    "EscalationManager",
    "ToneAdjuster",
]
