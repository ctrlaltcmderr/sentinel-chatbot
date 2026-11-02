"""
Document Retriever - Retrieves relevant documents with access control and temporal filtering.

Handles:
- Access level hierarchy enforcement (public < internal < restricted < confidential)
- Temporal policy resolution (current vs. historical queries)
- TF-IDF-like relevance scoring
- Conflict resolution via PolicyResolver
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from ..core.models.data_models import KnowledgeDocument, AccessLevel
from ..core.utils.helpers import TimeProvider, get_logger

from .document_store import DocumentStore
from .policy_resolver import PolicyResolver
from .safety_checker import SafetyChecker
from .query_intent import QueryIntent, classify_query_intent, is_document_relevant_to_intent



logger = get_logger("rag.retriever")

# Access level hierarchy: higher index = more privileged
ACCESS_LEVEL_HIERARCHY: Dict[str, int] = {
    AccessLevel.PUBLIC.value: 0,
    AccessLevel.INTERNAL.value: 1,
    AccessLevel.RESTRICTED.value: 2,
    AccessLevel.CONFIDENTIAL.value: 3,
}


class DocumentRetriever:
    """
    Retrieves relevant documents from the document store, respecting
    access control, temporal constraints, and relevance ranking.
    """

    def __init__(
        self,
        document_store: DocumentStore,
        policy_resolver: Optional[PolicyResolver] = None,
        safety_checker: Optional[SafetyChecker] = None,
        time_provider: type = TimeProvider,
    ) -> None:
        """
        Args:
            document_store: The document store to query.
            policy_resolver: Policy resolver for conflict handling. Created if None.
            safety_checker: Safety checker for query validation. Created if None.
            time_provider: Class providing .now() for current time.
        """
        self._store = document_store
        self._policy_resolver = policy_resolver or PolicyResolver(time_provider=time_provider)
        self._safety_checker = safety_checker or SafetyChecker()
        self._time_provider = time_provider

    def retrieve(
        self,
        query: str,
        user_access_level: str,
        reference_date: Optional[datetime] = None,
        filters: Optional[Dict] = None,
    ) -> List[KnowledgeDocument]:
        """
        Retrieve documents relevant to a query, filtered by access and temporal constraints.

        Args:
            query: The search query text.
            user_access_level: The user's access level (e.g. "public", "internal").
            reference_date: Optional date for historical queries. If None, uses current time.
            filters: Optional metadata filters (product, region, tags, etc.).

        Returns:
            List of matching KnowledgeDocument objects, ranked by relevance.
            Restricted/unauthorized and temporally-invalid documents are excluded.
        """
        filters = filters or {}

        # Step 0: Check query safety
        is_safe, issues = self._safety_checker.check_query(query)
        if not is_safe:
            logger.warning(f"Unsafe query detected during retrieval: {issues}")
            return []

        # Step 1: Query Intent Relevance Check
        intent_res = classify_query_intent(query)
        if intent_res.intent == QueryIntent.ORDER_TRACKING:
            logger.info("Query identified as ORDER_TRACKING. Static policy documents excluded.")
            return []

        # Step 2: Query the store with keyword search and metadata filters
        candidates = self._store.search(query=query, filters=filters)

        if not candidates:
            logger.info(f"No candidates found for query: '{query[:80]}'")
            return []

        # Step 3: Semantic Intent Filtering (ensure documents align with query intent)
        candidates = [
            doc for doc in candidates
            if is_document_relevant_to_intent(doc, intent_res.intent)
        ]

        if not candidates:
            logger.info(f"No candidates aligned with intent '{intent_res.intent.value}' for query: '{query[:80]}'")
            return []

        # Step 4: Filter by access level
        candidates = self._filter_by_access_level(candidates, user_access_level)

        if not candidates:
            logger.info(f"No documents accessible at level '{user_access_level}'")
            return []

        # Step 5: Filter by temporal validity
        check_date = reference_date if reference_date is not None else self._time_provider.now()
        candidates = self._filter_by_temporal_validity(candidates, check_date)

        if not candidates:
            logger.info(f"No temporally valid documents for date {check_date.isoformat()}")
            return []

        # Step 6: Resolve conflicts among same-topic documents
        candidates = self._resolve_duplicates(candidates, reference_date)

        logger.info(
            f"Retrieved {len(candidates)} document(s) for query: '{query[:80]}' "
            f"(intent={intent_res.intent.value}, access={user_access_level})"
        )
        return candidates


    def _filter_by_access_level(
        self,
        documents: List[KnowledgeDocument],
        user_access_level: str,
    ) -> List[KnowledgeDocument]:
        """
        Filter documents to those the user is authorized to see.

        Access hierarchy: public < internal < restricted < confidential.
        A user at a given level can see documents at or below that level.
        """
        user_level = ACCESS_LEVEL_HIERARCHY.get(user_access_level, 0)

        filtered = []
        for doc in documents:
            doc_level = ACCESS_LEVEL_HIERARCHY.get(doc.access_level.value, 0)
            if doc_level <= user_level:
                filtered.append(doc)
            else:
                logger.debug(
                    f"Access denied: doc '{doc.title}' requires {doc.access_level.value}, "
                    f"user has {user_access_level}"
                )
        return filtered

    def _filter_by_temporal_validity(
        self,
        documents: List[KnowledgeDocument],
        check_date: datetime,
    ) -> List[KnowledgeDocument]:
        """
        Filter documents to those active at the given date.

        A document is active when:
        - effective_date <= check_date (or effective_date is None)
        - expiry_date > check_date (or expiry_date is None)
        """
        return self._policy_resolver.filter_active(documents, at_date=check_date)

    def _resolve_duplicates(
        self,
        documents: List[KnowledgeDocument],
        reference_date: Optional[datetime] = None,
    ) -> List[KnowledgeDocument]:
        """
        Group documents by product+title topic and resolve conflicts within each group.

        For each group with multiple documents, use PolicyResolver to select the best one.
        """
        if len(documents) <= 1:
            return documents

        # Group by (product, title_normalized) as a proxy for "same topic"
        from collections import defaultdict
        groups: Dict[str, List[KnowledgeDocument]] = defaultdict(list)
        for doc in documents:
            key = f"{doc.product.lower()}::{doc.title.lower().strip()}"
            groups[key].append(doc)

        resolved: List[KnowledgeDocument] = []
        for key, group_docs in groups.items():
            if len(group_docs) == 1:
                resolved.append(group_docs[0])
            else:
                winner = self._policy_resolver.resolve_conflict(
                    group_docs, reference_date=reference_date
                )
                if winner:
                    resolved.append(winner)

        return resolved
