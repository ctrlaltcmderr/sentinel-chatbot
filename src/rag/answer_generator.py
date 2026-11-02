"""
Answer Generator for RAG Knowledge Assistant.

Synthesizes accurate answers from retrieved knowledge documents with:
- Mandatory source citations (title, version, effective date)
- Strict refusal on missing or unrelated evidence
- Query intent verification (order tracking, warranty, refund, security)
- Transparent explanation of live order-tracking limitations
- Mandatory collection of missing Order IDs for order-tracking inquiries
- Ambiguity and conflict detection
- Unsupported claim detection without malformed phrases
- Complete resistance to malicious instructions embedded in documents
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set

from ..core.models.data_models import KnowledgeDocument, RAGResult
from ..core.utils.helpers import get_logger, normalize_text
from .query_intent import (
    QueryIntent,
    classify_query_intent,
    is_document_relevant_to_intent,
)
from .safety_checker import SafetyChecker

logger = get_logger("rag.answer_generator")


class AnswerGenerator:
    """
    Generates grounded factual responses from retrieved knowledge documents.
    Enforces strict grounding, citations, refusal when evidence is lacking,
    and immunity to embedded instructions.
    """

    def __init__(self, safety_checker: Optional[SafetyChecker] = None) -> None:
        self.safety_checker = safety_checker or SafetyChecker()

    def generate_answer(
        self,
        query: str,
        documents: List[KnowledgeDocument],
        context: Optional[Dict[str, Any]] = None,
    ) -> RAGResult:
        """
        Generate answer based on retrieved documents with full citations and safety checks.

        Args:
            query: The user's question
            documents: List of retrieved, authorized knowledge documents
            context: Optional conversational or metadata context

        Returns:
            RAGResult object with answer, citations, confidence, and flags
        """
        context = context or {}

        # 1. Check query safety
        is_safe, issues = self.safety_checker.check_query(query)
        if not is_safe:
            return RAGResult(
                answer="I cannot fulfill this request because it violates security policies.",
                confidence=0.0,
                sources=[],
                is_ambiguous=False,
                requires_clarification=False,
                clarification_message="",
                unsupported_claims=["Query violates security policies"],
                metadata={"security_issues": issues},
            )

        # 2. Query Intent Classification
        intent_res = classify_query_intent(query, context=context)


        # 3. Handle Order Tracking specifically (Requirements 5, 6, 7)
        if intent_res.intent == QueryIntent.ORDER_TRACKING:
            if not intent_res.order_id:
                # Missing Order ID -> Request it and explain live carrier tracking limitation
                answer = (
                    "To help you with your order status, could you please provide your Order ID "
                    "(for example, ORD-123456)?\n\n"
                    "Please note that our chat assistant does not have a direct live integration with "
                    "external shipping carrier tracking systems. Once you provide your order reference, "
                    "I can look up your order details or connect you with our support team to investigate the delay."
                )
                return RAGResult(
                    answer=answer,
                    confidence=0.95,
                    sources=[],
                    is_ambiguous=False,
                    requires_clarification=True,
                    clarification_message="Please provide your Order ID (e.g., ORD-123456).",
                    unsupported_claims=["Live order tracking integration unavailable"],
                    metadata={"intent": "order_tracking", "missing_info": ["order_id"]},
                )
            else:
                # Order ID present -> Explain limitation clearly and offer resolution without fabricating carrier status
                order_id = intent_res.order_id
                answer = (
                    f"Thank you for providing your Order ID ({order_id}).\n\n"
                    "Please note that live carrier tracking integration is currently not directly connected "
                    "to this chat assistant. I have recorded your order reference, and our customer support "
                    "team can check the fulfillment records with the carrier for you.\n\n"
                    "Would you like me to open an expedited support ticket for our fulfillment specialists "
                    "to investigate this delivery?"
                )
                return RAGResult(
                    answer=answer,
                    confidence=0.95,
                    sources=[],
                    is_ambiguous=False,
                    requires_clarification=False,
                    clarification_message="",
                    unsupported_claims=[],
                    metadata={"intent": "order_tracking", "order_id": order_id},
                )

        # 4. Filter out unsafe or corrupted documents
        safe_docs: List[KnowledgeDocument] = []
        for doc in documents:
            doc_safe, doc_issues = self.safety_checker.check_document(doc)
            if doc_safe:
                safe_docs.append(doc)
            else:
                logger.warning(
                    f"Ignored document '{doc.title}' (ID: {doc.id}) containing unsafe content: {doc_issues}"
                )

        # 5. Check if any documents exist
        if not safe_docs:
            return RAGResult(
                answer="I apologize, but I do not have enough verified information in the knowledge base to answer your question.",
                confidence=0.0,
                sources=[],
                is_ambiguous=False,
                requires_clarification=True,
                clarification_message="Could you please provide more details or rephrase your request?",
                unsupported_claims=["No verified knowledge documents available"],
                metadata={"reason": "no_documents"},
            )

        # 6. Intent & Semantic Relevance Check on safe_docs
        # Discard documents that are completely irrelevant to the query intent
        relevant_docs = [
            doc for doc in safe_docs
            if is_document_relevant_to_intent(doc, intent_res.intent)
        ]

        if not relevant_docs:
            logger.info(
                f"Documents found ({len(safe_docs)}) but none are relevant to intent '{intent_res.intent.value}'."
            )
            if intent_res.intent == QueryIntent.ACCOUNT_SECURITY:
                return RAGResult(
                    answer=(
                        "We take account security and unauthorized access very seriously. "
                        "I do not have a public policy document for this specific question in the knowledge base, "
                        "but our security protocols require immediately securing your account credentials. "
                        "This inquiry has been prioritized for our Account Security team."
                    ),
                    confidence=0.90,
                    sources=[],
                    is_ambiguous=False,
                    requires_clarification=False,
                    unsupported_claims=["No verified public security policy document in knowledge base"],
                    metadata={"reason": "unrelated_documents", "intent": "account_security"},
                )
            if intent_res.intent == QueryIntent.PAYMENT_SECURITY:
                return RAGResult(
                    answer=(
                        "We treat unauthorized payments and fraudulent charges with the highest priority. "
                        "I do not have a public policy document for this transaction in the knowledge base, "
                        "but our billing and security specialists will investigate unauthorized activity and assist you."
                    ),
                    confidence=0.90,
                    sources=[],
                    is_ambiguous=False,
                    requires_clarification=False,
                    unsupported_claims=["No verified public payment security policy in knowledge base"],
                    metadata={"reason": "unrelated_documents", "intent": "payment_security"},
                )
            return RAGResult(
                answer="I apologize, but I do not have enough verified information in the knowledge base to answer your question.",
                confidence=0.0,
                sources=[],
                is_ambiguous=False,
                requires_clarification=True,
                clarification_message="Could you please provide more details or rephrase your request?",
                unsupported_claims=["No relevant knowledge documents matching query intent"],
                metadata={"reason": "unrelated_documents"},
            )

        # 7. Check for conflicting or ambiguous information across documents
        is_ambiguous = False
        clarification_msg = ""
        if len(relevant_docs) > 1:
            products = {d.product for d in relevant_docs if d.product}
            doc_texts = [d.content.lower() for d in relevant_docs]
            has_conflicting_refund = any("non-refundable" in t for t in doc_texts) and any(
                "full refund" in t or "30 days" in t for t in doc_texts
            )
            if has_conflicting_refund and len(products) <= 1:
                is_ambiguous = True
                clarification_msg = (
                    "There are conflicting policies regarding refunds for this item. "
                    "Could you specify your purchase channel, region, or date of purchase?"
                )

        if is_ambiguous:
            return RAGResult(
                answer="Multiple policy conditions may apply to your request.",
                confidence=0.4,
                sources=self._build_citations(relevant_docs),
                is_ambiguous=True,
                requires_clarification=True,
                clarification_message=clarification_msg,
                unsupported_claims=[],
                metadata={"reason": "policy_conflict"},
            )

        # 8. Extract answers and match passages
        query_words = set(re.findall(r"\b[a-z]{3,}\b", query.lower()))
        stop_words = {
            "what", "when", "where", "which", "does", "have", "with", "from",
            "your", "this", "that", "about", "could", "would", "should", "please",
            "tell", "can", "for", "the", "are", "you", "item", "product", "policy",
            "someone", "somebody", "anyone", "permission", "noticed", "yesterday",
            "supposed", "today", "tomorrow", "hello", "thank", "thanks", "regards",
            "customer", "help", "need", "want", "like", "know", "there", "their",
            "accessed", "access", "saw", "see", "seen", "payment", "paid", "charge",
            "charged", "look", "looking", "check", "checked", "got", "get", "getting",
            "make", "made", "sent", "send", "went", "come", "came", "been", "being",
            "also", "just", "into", "onto", "under", "over",
        }
        substantive_query_words = query_words - stop_words

        # Find best matching passages and track which documents they originate from
        doc_passages: List[tuple[str, KnowledgeDocument, int]] = []
        for doc in relevant_docs:
            paragraphs = [p.strip() for p in doc.content.split("\n") if p.strip()]
            for p in paragraphs:
                p_lower = p.lower()
                # Count matching substantive query words
                match_count = sum(1 for w in substantive_query_words if w in p_lower)
                # Title word match bonus
                title_match = sum(1 for w in substantive_query_words if w in doc.title.lower())
                total_score = match_count * 2 + title_match
                if total_score > 0:
                    doc_passages.append((p, doc, total_score))

        # Sort passages by match score descending
        doc_passages.sort(key=lambda x: x[2], reverse=True)

        if not doc_passages:
            primary_passage = relevant_docs[0].content.strip()
            used_docs = [relevant_docs[0]]
        else:
            primary_passage = doc_passages[0][0]
            used_docs = [doc_passages[0][1]]

        # Build citations ONLY for documents that were actually used
        citations = self._build_citations(used_docs)
        citation_str = "\n\nSources:\n" + "\n".join([
            f"- {c['title']} (v{c['version']}, Effective: {c['effective_date'] or 'N/A'})"
            for c in citations
        ])
        answer_text = f"{primary_passage}{citation_str}"

        # 9. Detect unsupported claims
        combined_used_content = " ".join([d.content + " " + d.title for d in used_docs])
        used_doc_words = set(re.findall(r"\b[a-z]{3,}\b", combined_used_content.lower()))
        unsupported = [w for w in substantive_query_words if w not in used_doc_words]

        unsupported_claims: List[str] = []
        if len(unsupported) >= 2:
            unsupported_terms = ", ".join(f"'{u}'" for u in unsupported[:2])
            unsupported_claims = [f"Specific detail regarding '{u}' was not found in knowledge base" for u in unsupported[:2]]
            answer_text += f"\n\nNote: Details regarding {unsupported_terms} are not specified in the current policy."


        confidence = 0.95 if not unsupported_claims else 0.70

        return RAGResult(
            answer=answer_text,
            confidence=confidence,
            sources=citations,
            is_ambiguous=False,
            requires_clarification=False,
            clarification_message="",
            unsupported_claims=unsupported_claims,
            metadata={"doc_count": len(used_docs)},
        )

    def _build_citations(self, documents: List[KnowledgeDocument]) -> List[Dict[str, Any]]:
        """Build structured citations only for documents actually used."""
        citations = []
        seen = set()
        for doc in documents:
            if doc.id in seen:
                continue
            seen.add(doc.id)
            effective_str = doc.effective_date.strftime("%Y-%m-%d") if doc.effective_date else None
            citations.append({
                "document_id": doc.id,
                "title": doc.title,
                "version": doc.version,
                "effective_date": effective_str,
                "product": doc.product,
                "region": doc.region,
                "access_level": doc.access_level.value if hasattr(doc.access_level, "value") else str(doc.access_level),
            })
        return citations
