"""
Policy Resolver - Handles conflict resolution among multiple documents.

When multiple policies exist for the same topic, this module determines
which one takes precedence based on version numbers, effective dates,
and expiry dates.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from ..core.models.data_models import KnowledgeDocument, DocumentStatus
from ..core.utils.helpers import TimeProvider, get_logger


logger = get_logger("rag.policy_resolver")


class PolicyResolver:
    """
    Resolves conflicts among multiple knowledge documents / policies.

    Rules:
    - For current queries: pick the latest version with valid effective/expiry dates.
    - For historical queries: pick the version active on the reference date.
    """

    def __init__(self, time_provider: type = TimeProvider) -> None:
        """
        Args:
            time_provider: Class providing .now() for current time (default: TimeProvider).
        """
        self._time_provider = time_provider

    def is_policy_active(
        self,
        doc: KnowledgeDocument,
        at_date: Optional[datetime] = None,
    ) -> bool:
        """
        Check whether a policy/document is active at a given date.

        A document is active when:
        1. Its status is not QUARANTINED or ARCHIVED.
        2. effective_date <= check_date (or effective_date is None).
        3. expiry_date > check_date (or expiry_date is None).

        Args:
            doc: The document to check.
            at_date: The date to check against. Defaults to TimeProvider.now().

        Returns:
            True if the document is active at the specified date.
        """
        if doc.status in (DocumentStatus.QUARANTINED, DocumentStatus.ARCHIVED):
            return False

        check_date = at_date if at_date is not None else self._time_provider.now()

        # Check effective_date constraint
        if doc.effective_date is not None and doc.effective_date > check_date:
            return False

        # Check expiry_date constraint
        if doc.expiry_date is not None and doc.expiry_date <= check_date:
            return False

        return True

    def resolve_conflict(
        self,
        documents: List[KnowledgeDocument],
        reference_date: Optional[datetime] = None,
    ) -> Optional[KnowledgeDocument]:
        """
        Resolve conflicts among multiple documents by selecting the best one.

        Selection logic:
        1. Filter to only active documents (at reference_date or now).
        2. Among active documents, select the one with the highest version number.
        3. If versions are equal, prefer the one with the latest effective_date.

        Args:
            documents: List of candidate documents.
            reference_date: Optional date for historical queries.

        Returns:
            The winning document, or None if no active documents remain.
        """
        if not documents:
            return None

        check_date = reference_date if reference_date is not None else self._time_provider.now()

        # Filter to active documents
        active_docs = [
            doc for doc in documents
            if self.is_policy_active(doc, at_date=check_date)
        ]

        if not active_docs:
            logger.info(
                f"No active documents found among {len(documents)} candidates "
                f"at date {check_date.isoformat()}"
            )
            return None

        # Sort by version descending, then by effective_date descending (latest first)
        def sort_key(doc: KnowledgeDocument) -> tuple:
            eff = doc.effective_date if doc.effective_date else datetime.min
            return (doc.version, eff)

        active_docs.sort(key=sort_key, reverse=True)
        winner = active_docs[0]

        logger.info(
            f"Resolved conflict: selected '{winner.title}' v{winner.version} "
            f"(id={winner.id}) from {len(active_docs)} active candidates"
        )
        return winner

    def filter_active(
        self,
        documents: List[KnowledgeDocument],
        at_date: Optional[datetime] = None,
    ) -> List[KnowledgeDocument]:
        """
        Filter a list of documents to only those active at the given date.

        Args:
            documents: List of documents to filter.
            at_date: The date to check against. Defaults to now.

        Returns:
            List of active documents.
        """
        return [
            doc for doc in documents
            if self.is_policy_active(doc, at_date=at_date)
        ]
