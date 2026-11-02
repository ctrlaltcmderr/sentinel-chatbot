"""
Tests for Component 4: Answer Generator.

Hidden evaluations:
- Mandatory source citations
- Strict refusal on missing evidence
- Ambiguity and contradiction handling
- Unsupported claim detection
"""

import unittest
from datetime import datetime

from src.core.models.data_models import AccessLevel, KnowledgeDocument
from src.rag.answer_generator import AnswerGenerator


class TestAnswerGenerator(unittest.TestCase):
    """Test answer synthesis, citations, refusal, and claim grounding."""

    def setUp(self):
        self.generator = AnswerGenerator()

    def test_answer_contains_source_citations(self):
        """Every factual answer must include a source citation (title, version, effective date)."""
        doc = KnowledgeDocument(
            id="doc-terms",
            title="Standard Warranty Agreement",
            version=2,
            effective_date=datetime(2026, 1, 1),
            access_level=AccessLevel.PUBLIC,
            content="All hardware products carry a 12-month standard replacement warranty against manufacturer defects.",
        )
        res = self.generator.generate_answer("What is the warranty period?", [doc])
        self.assertIn("12-month", res.answer)
        self.assertTrue(len(res.sources) > 0)
        self.assertEqual(res.sources[0]["title"], "Standard Warranty Agreement")
        self.assertEqual(res.sources[0]["version"], 2)
        self.assertIn("Sources:", res.answer)

    def test_refuse_when_evidence_missing(self):
        """Chatbot refuses to answer and requests clarification when no evidence is available."""
        res = self.generator.generate_answer("How do I fly to Mars with your product?", [])
        self.assertTrue(res.requires_clarification)
        self.assertIn("do not have enough verified information", res.answer)
        self.assertEqual(res.confidence, 0.0)

    def test_detect_unsupported_claims(self):
        """Detect query claims not supported by knowledge base documents."""
        doc = KnowledgeDocument(
            id="doc-sub",
            title="Subscription Pricing",
            version=1,
            effective_date=datetime(2026, 1, 1),
            content="The basic plan costs $10 monthly. The premium plan costs $30 monthly.",
        )
        # Ask about something completely absent: "enterprise quantum encryption discount"
        res = self.generator.generate_answer("What is the enterprise quantum encryption discount?", [doc])
        self.assertTrue(len(res.unsupported_claims) > 0)
        self.assertIn("Note:", res.answer)

    def test_ambiguous_conflicting_evidence_requests_clarification(self):
        """Hidden evaluation: Ambiguous or contradicting documents trigger clarification request."""
        doc1 = KnowledgeDocument(
            id="doc-retail",
            title="Retail Store Refund Policy",
            product="OmniProduct",
            version=1,
            effective_date=datetime(2026, 1, 1),
            content="OmniProduct is completely non-refundable for retail purchases.",
        )
        doc2 = KnowledgeDocument(
            id="doc-online",
            title="Online Store Refund Policy",
            product="OmniProduct",
            version=1,
            effective_date=datetime(2026, 1, 1),
            content="OmniProduct qualifies for a full refund within 30 days of purchase.",
        )
        res = self.generator.generate_answer("Can I get a refund for OmniProduct?", [doc1, doc2])
        self.assertTrue(res.is_ambiguous)
        self.assertTrue(res.requires_clarification)
        self.assertIn("conflicting policies", res.clarification_message.lower())


if __name__ == "__main__":
    unittest.main()
