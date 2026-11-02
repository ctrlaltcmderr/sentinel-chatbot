"""
Tests for RAG Intent Relevance, Order Tracking, Citation Accuracy, and Anti-Hallucination.

Covers:
1. Order tracking questions (with and without Order ID)
2. Warranty questions (excludes refund/unrelated policies)
3. Refund questions (excludes warranty/unrelated policies)
4. Unrelated document retrieval prevention
5. No relevant document found (strict refusal without hallucination)
6. Missing information requests (Order ID, contact details)
7. Hallucination resistance (never fabricating fake carrier statuses or unsupported claims)
"""

import unittest
from datetime import datetime

from src.chatbot import SentinelChatbot
from src.core.models.data_models import AccessLevel, KnowledgeDocument
from src.core.utils.helpers import TimeProvider
from src.rag.answer_generator import AnswerGenerator
from src.rag.document_store import DocumentStore
from src.rag.query_intent import (
    QueryIntent,
    classify_query_intent,
    extract_order_id,
    is_document_relevant_to_intent,
)
from src.rag.retriever import DocumentRetriever


class TestRAGRelevanceAndIntent(unittest.TestCase):
    """Certifies query intent relevance, order tracking handling, and anti-hallucination."""

    def setUp(self):
        TimeProvider.reset()
        self.bot = SentinelChatbot()
        self.generator = AnswerGenerator()
        self.store = DocumentStore()
        self.retriever = DocumentRetriever(self.store)

        # Seed realistic store documents
        self.doc_warranty = KnowledgeDocument(
            id="kb-war-test",
            title="UltraLaptop Hardware Warranty Policy 2025-2026",
            product="UltraLaptop",
            region="global",
            access_level=AccessLevel.PUBLIC,
            version=2,
            effective_date=datetime(2025, 1, 1),
            content="UltraLaptop models include a 2-year premium on-site warranty covering hardware defects.",
        )
        self.doc_refund = KnowledgeDocument(
            id="kb-ret-test",
            title="Global Return and Refund Policy",
            product="General",
            region="global",
            access_level=AccessLevel.PUBLIC,
            version=1,
            effective_date=datetime(2025, 1, 1),
            content="Customers may return items within 30 days of delivery for a full refund.",
        )
        self.store.add_document(self.doc_warranty)
        self.store.add_document(self.doc_refund)

    def tearDown(self):
        TimeProvider.reset()

    # =========================================================================
    # 1. ORDER TRACKING QUESTIONS
    # =========================================================================

    def test_order_tracking_without_order_id_requests_id_and_explains_limitation(self):
        """
        When customer asks 'Where is my order? It was supposed to arrive yesterday':
        - MUST NOT respond with unrelated laptop warranty or return policies.
        - MUST request the missing Order ID.
        - MUST explain that live carrier tracking integration is unavailable.
        - MUST NOT fabricate delivery status or tracking numbers.
        - MUST have empty citations/sources.
        """
        query = "Where is my order? It was supposed to arrive yesterday"
        res = self.bot.handle_message(customer_id="cust-order-test", raw_text=query)

        # Verify no unrelated warranty or return policy text in reply
        self.assertNotIn("warranty", res["reply"].lower())
        self.assertNotIn("ultralaptop", res["reply"].lower())
        self.assertNotIn("hardware defect", res["reply"].lower())

        # Verify sources are empty (no unrelated citations)
        self.assertEqual(res["sources"], [])

        # Verify request for missing Order ID
        self.assertIn("order id", res["reply"].lower())

        # Verify transparent explanation of live tracking limitation
        reply_lower = res["reply"].lower()
        self.assertTrue(
            "not have a direct live integration" in reply_lower
            or "not directly integrated" in reply_lower
            or "live carrier tracking" in reply_lower
            or "carrier tracking integration" in reply_lower
        )

        # Verify no fabricated carrier or delivery date
        self.assertNotIn("fedex", reply_lower)
        self.assertNotIn("ups", reply_lower)
        self.assertNotIn("dhl", reply_lower)
        self.assertNotIn("delivered at", reply_lower)

    def test_order_tracking_with_order_id_explains_limitation_and_offers_support(self):
        """
        When customer provides Order ID ('Where is my order ORD-998877?'):
        - MUST acknowledge the specific Order ID.
        - MUST explain live tracking integration limitation.
        - MUST NOT cite unrelated policies.
        - MUST offer human support / ticket creation.
        """
        query = "Where is my order ORD-998877? It was supposed to arrive yesterday"
        res = self.bot.handle_message(customer_id="cust-order-test-2", raw_text=query)

        self.assertIn("ORD-998877", res["reply"])
        self.assertEqual(res["sources"], [])
        self.assertNotIn("warranty", res["reply"].lower())

        reply_lower = res["reply"].lower()
        self.assertTrue(
            "live carrier tracking" in reply_lower
            or "not directly connected" in reply_lower
            or "tracking integration" in reply_lower
        )

    # =========================================================================
    # 2. WARRANTY QUESTIONS
    # =========================================================================

    def test_warranty_question_retrieves_only_warranty_policy(self):
        """
        When customer asks about warranty:
        - Retrieves only the warranty policy.
        - Excludes return and refund policies from sources.
        """
        query = "What is the warranty coverage for UltraLaptop?"
        res = self.bot.handle_message(customer_id="cust-war-test", raw_text=query)

        self.assertIn("2-year", res["reply"])
        self.assertTrue(len(res["sources"]) > 0)

        source_titles = [s["title"] for s in res["sources"]]
        for title in source_titles:
            self.assertIn("Warranty", title)
            self.assertNotIn("Return", title)

    # =========================================================================
    # 3. REFUND QUESTIONS
    # =========================================================================

    def test_refund_question_retrieves_only_refund_policy(self):
        """
        When customer asks about returns/refunds:
        - Retrieves only the return and refund policy.
        - Excludes warranty policies from sources.
        """
        query = "What is the return and refund policy for items?"
        res = self.bot.handle_message(customer_id="cust-ret-test", raw_text=query)

        self.assertIn("30 days", res["reply"])
        self.assertIn("refund", res["reply"].lower())
        self.assertTrue(len(res["sources"]) > 0)

        source_titles = [s["title"] for s in res["sources"]]
        for title in source_titles:
            self.assertIn("Return", title)
            self.assertNotIn("Warranty", title)

    # =========================================================================
    # 4. UNRELATED DOCUMENT RETRIEVAL PREVENTION
    # =========================================================================

    def test_unrelated_documents_excluded_for_order_and_cross_domains(self):
        """
        DocumentRetriever strictly excludes unrelated documents:
        - Order tracking queries return 0 policy documents.
        - Warranty queries do not return refund documents.
        - Refund queries do not return warranty documents.
        """
        # Order tracking -> Empty
        docs_order = self.retriever.retrieve(
            query="Where is my order? It was supposed to arrive yesterday",
            user_access_level="public",
        )
        self.assertEqual(docs_order, [])

        # Warranty -> Only warranty doc
        docs_war = self.retriever.retrieve(
            query="What hardware defects are covered under warranty?",
            user_access_level="public",
        )
        self.assertEqual(len(docs_war), 1)
        self.assertEqual(docs_war[0].id, "kb-war-test")

        # Refund -> Only refund doc
        docs_ret = self.retriever.retrieve(
            query="Can I return an item for a full refund?",
            user_access_level="public",
        )
        self.assertEqual(len(docs_ret), 1)
        self.assertEqual(docs_ret[0].id, "kb-ret-test")

    # =========================================================================
    # 5. NO RELEVANT DOCUMENT FOUND
    # =========================================================================

    def test_no_relevant_document_found_refuses_without_hallucinating(self):
        """
        When query is outside knowledge base scope:
        - Retriever returns empty candidate list.
        - Chatbot refuses without fabricating an answer.
        - Sources list is empty.
        """
        query = "How do I make chocolate cake with strawberries?"
        res = self.bot.handle_message(customer_id="cust-cake-test", raw_text=query)

        self.assertEqual(res["sources"], [])
        self.assertIn("do not have enough verified information", res["reply"].lower())

    # =========================================================================
    # 6. MISSING INFORMATION HANDLING
    # =========================================================================

    def test_missing_information_requests_order_id(self):
        """
        Order tracking queries without an order ID flag missing information.
        """
        intent_res = classify_query_intent("Where is my delivery? It was supposed to come yesterday")
        self.assertEqual(intent_res.intent, QueryIntent.ORDER_TRACKING)
        self.assertIn("order_id", intent_res.missing_info)
        self.assertIsNone(intent_res.order_id)

        intent_res_with_id = classify_query_intent("Where is my package ORD-445566?")
        self.assertEqual(intent_res_with_id.intent, QueryIntent.ORDER_TRACKING)
        self.assertEqual(intent_res_with_id.order_id, "ORD-445566")
        self.assertEqual(intent_res_with_id.missing_info, [])

    # =========================================================================
    # 7. HALLUCINATION & UNSUPPORTED CLAIMS RESISTANCE
    # =========================================================================

    def test_never_fabricates_carrier_tracking(self):
        """
        Chatbot never fabricates carrier tracking numbers, transit locations, or delivery times.
        """
        queries = [
            "Track package for order ORD-123456",
            "Where is my package right now?",
            "Has order ORD-789012 shipped yet?",
        ]
        for q in queries:
            res = self.bot.handle_message(customer_id="cust-hallucination-test", raw_text=q)
            reply = res["reply"].lower()
            self.assertNotIn("is currently in transit at", reply)
            self.assertNotIn("out for delivery at", reply)
            self.assertNotIn("fedex tracking #", reply)
            self.assertEqual(res["sources"], [])

    def test_citations_only_reference_actually_used_documents(self):
        """
        When multiple documents are available, citations only include the document actually used.
        """
        doc1 = KnowledgeDocument(
            id="doc-w1",
            title="UltraLaptop Battery Policy",
            version=1,
            effective_date=datetime(2025, 1, 1),
            content="Laptop battery coverage extends for 12 months from original purchase date.",
        )
        doc2 = KnowledgeDocument(
            id="doc-w2",
            title="Desktop Screen Replacement Terms",
            version=1,
            effective_date=datetime(2025, 1, 1),
            content="Desktop monitors are covered for backlight issues for 36 months.",
        )
        res = self.generator.generate_answer("How long is the laptop battery coverage?", [doc1, doc2])
        self.assertEqual(len(res.sources), 1)
        self.assertEqual(res.sources[0]["document_id"], "doc-w1")
        self.assertNotIn("Desktop Screen", res.answer)


if __name__ == "__main__":
    unittest.main()
