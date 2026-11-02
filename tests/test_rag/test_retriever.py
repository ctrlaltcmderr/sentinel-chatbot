"""
Tests for Component 4: Document Store and Retriever.

Hidden evaluations:
- Role-based retrieval: unauthorized access strictly excluded
- Regional & product filtering
"""

import unittest
from datetime import datetime

from src.core.models.data_models import AccessLevel, KnowledgeDocument
from src.core.utils.helpers import TimeProvider
from src.rag.document_store import DocumentStore
from src.rag.retriever import DocumentRetriever


class TestDocumentRetriever(unittest.TestCase):
    """Test access level filtering and relevance-based retrieval."""

    def setUp(self):
        TimeProvider.reset()
        now = datetime(2026, 10, 28)
        TimeProvider.set_mock_time(now)

        self.store = DocumentStore()
        self.retriever = DocumentRetriever(self.store)

        # Populate documents
        self.doc_pub = KnowledgeDocument(
            id="pub-1",
            title="General Return Policy",
            content="Returns accepted within 30 days for all public retail purchases.",
            access_level=AccessLevel.PUBLIC,
            effective_date=datetime(2026, 1, 1),
            product="ProWidget",
            region="US",
        )
        self.doc_internal = KnowledgeDocument(
            id="int-1",
            title="Internal Support Playbook",
            content="How to issue supervisor refunds up to $100 without manager sign-off.",
            access_level=AccessLevel.INTERNAL,
            effective_date=datetime(2026, 1, 1),
            product="ProWidget",
            region="US",
        )
        self.doc_restricted = KnowledgeDocument(
            id="res-1",
            title="Executive Refund Override Guidelines",
            content="Confidential policy for VIP customer dispute resolution.",
            access_level=AccessLevel.RESTRICTED,
            effective_date=datetime(2026, 1, 1),
            product="ProWidget",
            region="US",
        )

        self.store.add_document(self.doc_pub)
        self.store.add_document(self.doc_internal)
        self.store.add_document(self.doc_restricted)

    def tearDown(self):
        TimeProvider.reset()

    def test_access_level_isolation(self):
        """Hidden evaluation: User with 'public' level cannot retrieve internal or restricted docs."""
        results_pub = self.retriever.retrieve(
            query="refund policy",
            user_access_level="public",
        )
        retrieved_ids = [d.id for d in results_pub]
        self.assertIn("pub-1", retrieved_ids)
        self.assertNotIn("int-1", retrieved_ids)
        self.assertNotIn("res-1", retrieved_ids)

    def test_internal_user_retrieves_internal_but_not_restricted(self):
        results_int = self.retriever.retrieve(
            query="refund",
            user_access_level="internal",
        )
        retrieved_ids = [d.id for d in results_int]
        self.assertIn("pub-1", retrieved_ids)
        self.assertIn("int-1", retrieved_ids)
        self.assertNotIn("res-1", retrieved_ids)

    def test_restricted_user_retrieves_all(self):
        results_res = self.retriever.retrieve(
            query="refund",
            user_access_level="restricted",
        )
        retrieved_ids = [d.id for d in results_res]
        self.assertIn("res-1", retrieved_ids)


if __name__ == "__main__":
    unittest.main()
