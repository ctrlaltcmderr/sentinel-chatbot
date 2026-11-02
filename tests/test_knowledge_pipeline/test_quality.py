"""
Tests for Component 3: Quality Tester.
"""

import unittest

from src.core.models.data_models import KnowledgeDocument
from src.knowledge_pipeline.quality_tester import QualityTester


class TestQualityTester(unittest.TestCase):
    """Test accuracy and grounding quality gates."""

    def setUp(self):
        self.tester = QualityTester()

    def test_approve_high_quality_update(self):
        existing = [
            KnowledgeDocument(
                id="doc-1",
                title="Return Policy",
                product="WidgetPro",
                content="Items may be returned within 30 days of purchase with receipt.",
                content_hash="hash-1",
            )
        ]
        new_docs = [
            KnowledgeDocument(
                id="doc-2",
                title="Return Exceptions",
                product="WidgetPro",
                content="Return Policy exceptions: Electronics must be in original packaging.",
                content_hash="hash-2",
            )
        ]
        results = self.tester.run_tests(new_docs, existing)
        self.assertTrue(results["approved"])
        self.assertGreaterEqual(results["accuracy_score"], 0.85)
        self.assertGreaterEqual(results["grounding_score"], 0.80)

    def test_reject_low_quality_contradictory_update(self):
        """Hidden evaluation: Reject updates that reduce accuracy or grounding."""
        existing = [
            KnowledgeDocument(
                id="doc-1",
                title="Warranty Policy",
                content="All laptops carry a 2-year manufacturer warranty.",
            )
        ]
        new_docs = [
            KnowledgeDocument(
                id="doc-2",
                title="Incomplete Doc",
                content="No details provided.",  # extremely short, lacks substance
            )
        ]
        results = self.tester.run_tests(new_docs, existing)
        # Completeness penalty should lower accuracy below threshold
        self.assertFalse(self.tester.should_approve(results))


if __name__ == "__main__":
    unittest.main()
