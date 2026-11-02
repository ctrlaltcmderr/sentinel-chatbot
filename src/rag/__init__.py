"""
RAG-Based Knowledge Assistant for Sentinel Chatbot.

Provides document storage, retrieval with access control,
temporal policy resolution, query intent analysis, answer generation
with citations, and safety checking.
"""

from .document_store import DocumentStore
from .retriever import DocumentRetriever
from .answer_generator import AnswerGenerator
from .policy_resolver import PolicyResolver
from .safety_checker import SafetyChecker
from .query_intent import (
    QueryIntent,
    QueryIntentResult,
    classify_query_intent,
    extract_order_id,
    is_document_relevant_to_intent,
)

__all__ = [
    "DocumentStore",
    "DocumentRetriever",
    "AnswerGenerator",
    "PolicyResolver",
    "SafetyChecker",
    "QueryIntent",
    "QueryIntentResult",
    "classify_query_intent",
    "extract_order_id",
    "is_document_relevant_to_intent",
]
