"""
Document Store - In-memory document storage with metadata indexing.

Provides fast lookups by product, region, access level, and full-text search
using keyword matching.
"""

from __future__ import annotations

import re
import math
from collections import defaultdict
from typing import Dict, List, Optional, Set

from ..core.models.data_models import KnowledgeDocument, AccessLevel, DocumentStatus
from ..core.utils.helpers import get_logger, normalize_text, compute_hash


logger = get_logger("rag.document_store")

# Domain synonyms to enhance retrieval recall across related concepts
SYNONYM_MAP: Dict[str, Set[str]] = {
    "refund": {"return", "returns", "refunds", "reimbursement"},
    "refunds": {"return", "returns", "refund", "reimbursement"},
    "return": {"refund", "refunds", "returns"},
    "returns": {"refund", "refunds", "return"},
    "warranty": {"guarantee", "warranties", "coverage"},
    "warranties": {"guarantee", "warranty", "coverage"},
    "guarantee": {"warranty", "warranties"},
}



class DocumentStore:
    """
    In-memory document store with metadata indexing.

    Supports adding, removing, and searching documents with filtering
    by product, region, access level, and keyword matching.
    """

    def __init__(self) -> None:
        # Primary store: doc_id -> KnowledgeDocument
        self._documents: Dict[str, KnowledgeDocument] = {}

        # Metadata indexes for fast filtering
        self._product_index: Dict[str, Set[str]] = defaultdict(set)
        self._region_index: Dict[str, Set[str]] = defaultdict(set)
        self._access_level_index: Dict[str, Set[str]] = defaultdict(set)
        self._tag_index: Dict[str, Set[str]] = defaultdict(set)

        # Inverted index for keyword search: term -> {doc_id: term_frequency}
        self._inverted_index: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        # Document lengths for TF-IDF normalization
        self._doc_lengths: Dict[str, int] = {}

    def add_document(self, doc: KnowledgeDocument) -> None:
        """
        Add a document to the store with metadata indexing.

        If a document with the same ID already exists, it is replaced.

        Args:
            doc: The KnowledgeDocument to add.
        """
        # Remove existing document if updating
        if doc.id in self._documents:
            self.remove_document(doc.id)

        # Compute content hash if not set
        if not doc.content_hash and doc.content:
            doc.content_hash = compute_hash(doc.content)

        # Store document
        self._documents[doc.id] = doc

        # Build metadata indexes
        if doc.product:
            self._product_index[doc.product.lower()].add(doc.id)
        if doc.region:
            self._region_index[doc.region.lower()].add(doc.id)
        self._access_level_index[doc.access_level.value].add(doc.id)
        for tag in doc.tags:
            self._tag_index[tag.lower()].add(doc.id)

        # Build inverted index for content search
        self._index_document_text(doc)

        logger.info(
            f"Added document '{doc.title}' (id={doc.id}, "
            f"product={doc.product}, version={doc.version})"
        )

    def remove_document(self, doc_id: str) -> bool:
        """
        Remove a document from the store and all indexes.

        Args:
            doc_id: The ID of the document to remove.

        Returns:
            True if document was found and removed, False otherwise.
        """
        doc = self._documents.pop(doc_id, None)
        if doc is None:
            return False

        # Clean metadata indexes
        if doc.product:
            self._product_index[doc.product.lower()].discard(doc_id)
        if doc.region:
            self._region_index[doc.region.lower()].discard(doc_id)
        self._access_level_index[doc.access_level.value].discard(doc_id)
        for tag in doc.tags:
            self._tag_index[tag.lower()].discard(doc_id)

        # Clean inverted index
        self._remove_from_inverted_index(doc_id)
        self._doc_lengths.pop(doc_id, None)

        logger.info(f"Removed document '{doc.title}' (id={doc_id})")
        return True

    def get_by_id(self, doc_id: str) -> Optional[KnowledgeDocument]:
        """
        Retrieve a document by its ID.

        Args:
            doc_id: The document identifier.

        Returns:
            The KnowledgeDocument if found, None otherwise.
        """
        return self._documents.get(doc_id)

    def search(
        self,
        query: str = "",
        filters: Optional[Dict] = None,
        min_relevance_threshold: float = 0.05,
    ) -> List[KnowledgeDocument]:
        """
        Search documents using keyword matching and metadata filters.

        Args:
            query: Text query for keyword search.
            filters: Dict of metadata filters. Supported keys:
                - product (str): Filter by product name
                - region (str): Filter by region
                - access_level (str): Filter by access level value
                - tags (List[str]): Filter by tags (any match)
                - status (str): Filter by document status
            min_relevance_threshold: Minimum TF-IDF relevance score required when query is provided.

        Returns:
            List of matching KnowledgeDocument objects, ranked by relevance.
        """
        filters = filters or {}

        # Start with all document IDs
        candidate_ids: Optional[Set[str]] = None

        # Apply metadata filters to narrow candidates
        if "product" in filters and filters["product"]:
            product_ids = self._product_index.get(filters["product"].lower(), set())
            candidate_ids = product_ids if candidate_ids is None else candidate_ids & product_ids

        if "region" in filters and filters["region"]:
            region_ids = self._region_index.get(filters["region"].lower(), set())
            candidate_ids = region_ids if candidate_ids is None else candidate_ids & region_ids

        if "access_level" in filters and filters["access_level"]:
            level_ids = self._access_level_index.get(filters["access_level"], set())
            candidate_ids = level_ids if candidate_ids is None else candidate_ids & level_ids

        if "tags" in filters and filters["tags"]:
            tag_ids: Set[str] = set()
            for tag in filters["tags"]:
                tag_ids |= self._tag_index.get(tag.lower(), set())
            candidate_ids = tag_ids if candidate_ids is None else candidate_ids & tag_ids

        # Fall back to all documents if no filters applied
        if candidate_ids is None:
            candidate_ids = set(self._documents.keys())

        # Apply status filter
        if "status" in filters and filters["status"]:
            candidate_ids = {
                doc_id for doc_id in candidate_ids
                if self._documents[doc_id].status.value == filters["status"]
            }

        # If query provided, score and rank by relevance
        if query.strip():
            scored = self._score_documents(query, candidate_ids)
            # Filter strictly by minimum relevance threshold - never return zero or irrelevant docs
            scored = [(doc_id, s) for doc_id, s in scored if s >= min_relevance_threshold]
            scored.sort(key=lambda x: x[1], reverse=True)
            return [self._documents[doc_id] for doc_id, _ in scored if doc_id in self._documents]
        else:
            return [self._documents[doc_id] for doc_id in candidate_ids if doc_id in self._documents]


    @property
    def document_count(self) -> int:
        """Return the number of documents in the store."""
        return len(self._documents)

    def get_all_documents(self) -> List[KnowledgeDocument]:
        """Return all documents in the store."""
        return list(self._documents.values())

    # ──────────────────── Internal Indexing Methods ────────────────────

    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into lowercase terms, removing stopwords."""
        # Simple tokenization: lowercase, split on non-alphanumeric
        tokens = re.findall(r"[a-z0-9]+", text.lower())
        # Comprehensive stopwords list: common auxiliaries, question words, pronouns, filler words
        stopwords = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "shall", "should", "may", "might", "must", "can",
            "could", "to", "of", "in", "for", "on", "with", "at", "by",
            "from", "as", "into", "through", "during", "before", "after",
            "above", "below", "between", "and", "but", "or", "not", "no",
            "this", "that", "these", "those", "it", "its",
            "what", "which", "who", "whom", "whose", "where", "when", "why", "how",
            "i", "me", "my", "myself", "we", "our", "ours", "you", "your", "yours",
            "he", "him", "his", "she", "her", "hers", "they", "them", "their", "theirs",
            "please", "tell", "show", "give", "quote", "say", "said", "ask", "asking",
            "want", "need", "know", "see", "get", "let", "just", "also", "about",
        }
        return [t for t in tokens if t not in stopwords and len(t) > 1]

    def _index_document_text(self, doc: KnowledgeDocument) -> None:
        """Build inverted index entries for a document's searchable text."""
        # Combine title, content, product, and tags for indexing
        text_parts = [doc.title, doc.content, doc.product]
        text_parts.extend(doc.tags)
        full_text = " ".join(text_parts)

        tokens = self._tokenize(full_text)
        self._doc_lengths[doc.id] = len(tokens) if tokens else 1

        for token in tokens:
            self._inverted_index[token][doc.id] += 1

    def _remove_from_inverted_index(self, doc_id: str) -> None:
        """Remove a document from the inverted index."""
        terms_to_clean = []
        for term, doc_freqs in self._inverted_index.items():
            if doc_id in doc_freqs:
                del doc_freqs[doc_id]
                if not doc_freqs:
                    terms_to_clean.append(term)
        for term in terms_to_clean:
            del self._inverted_index[term]

    def _score_documents(
        self, query: str, candidate_ids: Set[str]
    ) -> List[tuple[str, float]]:
        """
        Score documents against a query using TF-IDF ranking with title, keyword, and synonym weighting.

        Args:
            query: The search query.
            candidate_ids: Set of document IDs to consider.

        Returns:
            List of (doc_id, score) tuples with score > 0.
        """
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        total_docs = max(len(self._documents), 1)
        scores: Dict[str, float] = defaultdict(float)
        doc_matched_tokens: Dict[str, Set[str]] = defaultdict(set)

        generic_kb_terms = {
            "policy", "policies", "rule", "rules", "guide", "guidelines",
            "document", "documents", "article", "articles", "information",
            "info", "support", "help", "faq", "faqs", "current", "latest",
            "apply", "applies", "applied", "thing", "one", "another",
            "answer", "questions", "details", "terms",
        }
        substantive_tokens = [t for t in query_tokens if t not in generic_kb_terms]

        for token in query_tokens:
            tokens_to_check = [(token, 1.0)]
            for syn in SYNONYM_MAP.get(token, set()):
                tokens_to_check.append((syn, 0.85))

            for t, weight in tokens_to_check:
                if t not in self._inverted_index:
                    continue

                doc_freqs = self._inverted_index[t]
                df = len(doc_freqs)
                idf = (math.log((total_docs + 1) / (df + 1)) + 1.0) * weight

                for doc_id in candidate_ids:
                    if doc_id in doc_freqs:
                        tf = doc_freqs[doc_id]
                        doc_len = self._doc_lengths.get(doc_id, 1)
                        # Normalized TF
                        normalized_tf = tf / doc_len
                        scores[doc_id] += normalized_tf * idf
                        doc_matched_tokens[doc_id].add(token)

                        # Boost score if token appears in title or product name
                        doc = self._documents.get(doc_id)
                        if doc:
                            if t in doc.title.lower():
                                scores[doc_id] += 0.3 * idf
                            if doc.product and t in doc.product.lower():
                                scores[doc_id] += 0.2 * idf

        # Only return candidates that genuinely matched query tokens with positive score
        # If the query had substantive non-generic terms, the document MUST match at least one substantive token
        result = []
        for doc_id in candidate_ids:
            score = scores.get(doc_id, 0.0)
            if score > 0.0:
                if substantive_tokens:
                    matched = doc_matched_tokens.get(doc_id, set())
                    if not any(st in matched for st in substantive_tokens):
                        # Matched only generic terms (e.g. 'policy' or 'support') without substantive topic match
                        continue
                result.append((doc_id, score))

        return result


