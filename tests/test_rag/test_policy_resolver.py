"""
Tests for Component 4: Policy Resolver and Temporal Filtering.

Hidden evaluations:
- Conflicting policies: latest version among active ones wins
- Expired policy ignored for current questions
- Future-dated policy ignored for current questions
- Historical question retrieves policy active on specified date
"""

import unittest
from datetime import datetime

from src.core.models.data_models import KnowledgeDocument
from src.core.utils.helpers import TimeProvider
from src.rag.policy_resolver import PolicyResolver


class TestPolicyResolver(unittest.TestCase):
    """Test temporal resolution and conflict resolution for policies."""

    def setUp(self):
        TimeProvider.reset()
        self.resolver = PolicyResolver()

    def tearDown(self):
        TimeProvider.reset()

    def test_current_query_ignores_expired_and_future_policies(self):
        """Hidden evaluation: For current queries, ignore future and expired policies."""
        # Current time: 2026-10-28
        now = datetime(2026, 10, 28, 12, 0, 0)
        TimeProvider.set_mock_time(now)

        # Policy 1: Expired in 2025
        doc_expired = KnowledgeDocument(
            id="doc-expired",
            title="Return Policy 2024",
            product="CloudWidget",
            version=1,
            effective_date=datetime(2024, 1, 1),
            expiry_date=datetime(2025, 1, 1),
        )

        # Policy 2: Active currently (effective Jan 2025, no expiry)
        doc_active = KnowledgeDocument(
            id="doc-active",
            title="Return Policy 2025",
            product="CloudWidget",
            version=2,
            effective_date=datetime(2025, 1, 2),
            expiry_date=None,
        )

        # Policy 3: Future-dated (effective Dec 2026)
        doc_future = KnowledgeDocument(
            id="doc-future",
            title="Return Policy 2027 Preview",
            product="CloudWidget",
            version=3,
            effective_date=datetime(2026, 12, 1),
            expiry_date=None,
        )

        self.assertFalse(self.resolver.is_policy_active(doc_expired, at_date=now))
        self.assertTrue(self.resolver.is_policy_active(doc_active, at_date=now))
        self.assertFalse(self.resolver.is_policy_active(doc_future, at_date=now))

        resolved = self.resolver.resolve_conflict([doc_expired, doc_active, doc_future], reference_date=now)
        self.assertEqual(resolved.id, "doc-active")

    def test_historical_query_retrieves_policy_active_on_date(self):
        """Hidden evaluation: Historical queries retrieve policy active on specified customer date."""
        # Querying about a transaction on March 15, 2024
        historical_date = datetime(2024, 3, 15)

        doc_old = KnowledgeDocument(
            id="doc-v1",
            title="Refund Policy v1",
            version=1,
            effective_date=datetime(2023, 1, 1),
            expiry_date=datetime(2024, 6, 1),
        )
        doc_new = KnowledgeDocument(
            id="doc-v2",
            title="Refund Policy v2",
            version=2,
            effective_date=datetime(2024, 6, 2),
            expiry_date=datetime(2025, 6, 1),
        )

        self.assertTrue(self.resolver.is_policy_active(doc_old, at_date=historical_date))
        self.assertFalse(self.resolver.is_policy_active(doc_new, at_date=historical_date))

        resolved = self.resolver.resolve_conflict([doc_old, doc_new], reference_date=historical_date)
        self.assertEqual(resolved.id, "doc-v1")

    def test_conflicting_policies_latest_version_wins(self):
        """Hidden evaluation: When multiple active policies conflict, pick highest version."""
        now = datetime(2026, 10, 28)
        TimeProvider.set_mock_time(now)

        doc_v1 = KnowledgeDocument(
            id="doc-v1",
            title="Shipping Policy",
            version=1,
            effective_date=datetime(2026, 1, 1),
        )
        doc_v2 = KnowledgeDocument(
            id="doc-v2",
            title="Shipping Policy",
            version=2,
            effective_date=datetime(2026, 6, 1),
        )

        resolved = self.resolver.resolve_conflict([doc_v1, doc_v2], reference_date=now)
        self.assertEqual(resolved.id, "doc-v2")
        self.assertEqual(resolved.version, 2)


if __name__ == "__main__":
    unittest.main()
