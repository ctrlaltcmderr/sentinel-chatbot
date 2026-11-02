"""
Quality Tester – validates new knowledge documents against accuracy
and grounding thresholds before they are approved for the knowledge base.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Set

from ..core.config.settings import get_settings
from ..core.models.data_models import KnowledgeDocument
from ..core.utils.helpers import get_logger, normalize_text

logger = get_logger("knowledge_pipeline.quality_tester")


class QualityTester:
    """Run quality-gate tests on knowledge base updates."""

    def __init__(self, *, settings=None):
        self._settings = settings or get_settings()
        kb = self._settings.knowledge_base
        self._min_accuracy = kb.min_accuracy_threshold
        self._min_grounding = kb.min_grounding_threshold

    # ── public API ────────────────────────────────────────────────

    def run_tests(
        self,
        new_docs: List[KnowledgeDocument],
        existing_docs: List[KnowledgeDocument],
    ) -> Dict:
        """Run accuracy and grounding tests on the proposed update.

        Returns a dict with ``accuracy_score``, ``grounding_score``,
        per-document details, and overall ``approved`` flag.
        """
        accuracy_score = self._test_accuracy(new_docs, existing_docs)
        grounding_score = self._test_grounding(new_docs, existing_docs)

        results: Dict = {
            "accuracy_score": accuracy_score,
            "grounding_score": grounding_score,
            "min_accuracy_threshold": self._min_accuracy,
            "min_grounding_threshold": self._min_grounding,
            "details": {
                "new_doc_count": len(new_docs),
                "existing_doc_count": len(existing_docs),
                "completeness": self._check_completeness(new_docs),
                "contradictions": self._find_contradictions(new_docs, existing_docs),
                "ungrounded_claims": self._find_ungrounded_claims(new_docs, existing_docs),
            },
        }
        results["approved"] = self.should_approve(results)
        logger.info(
            "Quality test results: accuracy=%.2f, grounding=%.2f, approved=%s",
            accuracy_score,
            grounding_score,
            results["approved"],
        )
        return results

    def should_approve(self, test_results: Dict) -> bool:
        """Return True if scores meet both accuracy and grounding thresholds."""
        return (
            test_results["accuracy_score"] >= self._min_accuracy
            and test_results["grounding_score"] >= self._min_grounding
        )

    # ── accuracy testing ──────────────────────────────────────────

    def _test_accuracy(
        self,
        new_docs: List[KnowledgeDocument],
        existing_docs: List[KnowledgeDocument],
    ) -> float:
        """Calculate an accuracy score (0.0–1.0) considering completeness,
        consistency, and absence of contradictions.
        """
        if not new_docs:
            return 1.0

        completeness_scores = self._check_completeness(new_docs)
        avg_completeness = (
            sum(completeness_scores.values()) / len(completeness_scores)
            if completeness_scores
            else 1.0
        )

        contradictions = self._find_contradictions(new_docs, existing_docs)
        contradiction_penalty = min(len(contradictions) * 0.1, 0.5)

        # Consistency: documents with same product should not have conflicting info
        consistency_score = self._measure_consistency(new_docs)

        score = (avg_completeness * 0.4 + consistency_score * 0.3 + (1.0 - contradiction_penalty) * 0.3)
        return max(0.0, min(1.0, score))

    def _check_completeness(self, docs: List[KnowledgeDocument]) -> Dict[str, float]:
        """Check each document for key quality signals. Returns doc_id -> score."""
        scores: Dict[str, float] = {}
        for doc in docs:
            checks_passed = 0
            total_checks = 5

            # Has title
            if doc.title.strip():
                checks_passed += 1
            # Has non-trivial content (> 20 chars)
            if len(doc.content.strip()) > 20:
                checks_passed += 1
            # Has product
            if doc.product.strip():
                checks_passed += 1
            # Content is well-structured (has sentences / paragraphs)
            if "." in doc.content or "\n" in doc.content:
                checks_passed += 1
            # Has content hash (was properly processed)
            if doc.content_hash:
                checks_passed += 1

            scores[doc.id] = checks_passed / total_checks
        return scores

    def _find_contradictions(
        self,
        new_docs: List[KnowledgeDocument],
        existing_docs: List[KnowledgeDocument],
    ) -> List[Dict]:
        """Find contradictions between new and existing documents.

        Simple heuristic: if two documents cover the same product but have
        conflicting factual statements (negation patterns).
        """
        contradictions: List[Dict] = []
        all_docs = existing_docs + new_docs

        # Group by product
        product_groups: Dict[str, List[KnowledgeDocument]] = {}
        for doc in all_docs:
            if doc.product:
                product_groups.setdefault(doc.product.lower(), []).append(doc)

        for product, group in product_groups.items():
            if len(group) < 2:
                continue
            for i in range(len(group)):
                for j in range(i + 1, len(group)):
                    if self._has_negation_conflict(group[i].content, group[j].content):
                        contradictions.append({
                            "doc_a": group[i].id,
                            "doc_b": group[j].id,
                            "product": product,
                        })
        return contradictions

    @staticmethod
    def _has_negation_conflict(text_a: str, text_b: str) -> bool:
        """Detect if one text negates a statement from the other."""
        sentences_a = [s.strip() for s in re.split(r"[.!?]", text_a) if s.strip()]
        sentences_b = [s.strip() for s in re.split(r"[.!?]", text_b) if s.strip()]

        negation_words = {"not", "no", "never", "don't", "doesn't", "isn't", "aren't", "won't", "cannot"}

        for sa in sentences_a:
            na = normalize_text(sa)
            na_words = set(na.split())
            for sb in sentences_b:
                nb = normalize_text(sb)
                nb_words = set(nb.split())

                shared = na_words & nb_words - negation_words
                if len(shared) < 3:
                    continue  # sentences too dissimilar

                a_neg = bool(na_words & negation_words)
                b_neg = bool(nb_words & negation_words)
                if a_neg != b_neg:
                    return True
        return False

    @staticmethod
    def _measure_consistency(docs: List[KnowledgeDocument]) -> float:
        """Consistency: documents with same product should agree in tone."""
        if len(docs) <= 1:
            return 1.0

        product_groups: Dict[str, List[KnowledgeDocument]] = {}
        for doc in docs:
            key = doc.product.lower() if doc.product else "_no_product"
            product_groups.setdefault(key, []).append(doc)

        consistent_groups = 0
        for group in product_groups.values():
            if len(group) <= 1:
                consistent_groups += 1
                continue
            # Check all pairs for contradictions
            has_contradiction = False
            for i in range(len(group)):
                for j in range(i + 1, len(group)):
                    if QualityTester._has_negation_conflict(
                        group[i].content, group[j].content
                    ):
                        has_contradiction = True
                        break
                if has_contradiction:
                    break
            if not has_contradiction:
                consistent_groups += 1

        return consistent_groups / len(product_groups) if product_groups else 1.0

    # ── grounding testing ─────────────────────────────────────────

    def _test_grounding(
        self,
        new_docs: List[KnowledgeDocument],
        existing_docs: List[KnowledgeDocument],
    ) -> float:
        """Calculate a grounding score (0.0–1.0).

        Grounding checks that factual claims in new documents have supporting
        evidence in either the document itself or the existing corpus.
        """
        if not new_docs:
            return 1.0

        corpus_text = " ".join(
            normalize_text(d.content) for d in existing_docs if d.content
        )

        total_claims = 0
        grounded_claims = 0

        for doc in new_docs:
            claims = self._extract_claims(doc.content)
            total_claims += len(claims)
            for claim in claims:
                if self._is_grounded(claim, doc.content, corpus_text):
                    grounded_claims += 1

        if total_claims == 0:
            return 1.0
        return grounded_claims / total_claims

    @staticmethod
    def _extract_claims(content: str) -> List[str]:
        """Extract factual claim-like sentences from content."""
        sentences = re.split(r"[.!?]", content)
        claims: List[str] = []
        # A claim contains at least a subject-verb pattern (very rough heuristic)
        claim_indicators = {"is", "are", "was", "were", "has", "have", "will", "can", "must", "should", "provides", "supports", "offers", "includes", "requires"}
        for s in sentences:
            s = s.strip()
            if not s or len(s) < 10:
                continue
            words = set(normalize_text(s).split())
            if words & claim_indicators:
                claims.append(s)
        return claims

    @staticmethod
    def _is_grounded(claim: str, doc_content: str, corpus_text: str) -> bool:
        """Check if a claim has supporting content."""
        claim_norm = normalize_text(claim)
        claim_words = set(claim_norm.split())
        if len(claim_words) < 3:
            return True  # Too short to judge

        # Check for keyword overlap with corpus (simple grounding)
        meaningful_words = {w for w in claim_words if len(w) > 3}
        if not meaningful_words:
            return True

        doc_norm = normalize_text(doc_content)
        corpus_combined = doc_norm + " " + corpus_text
        corpus_words = set(corpus_combined.split())

        overlap = meaningful_words & corpus_words
        overlap_ratio = len(overlap) / len(meaningful_words) if meaningful_words else 1.0
        return overlap_ratio >= 0.5

    def _find_ungrounded_claims(
        self,
        new_docs: List[KnowledgeDocument],
        existing_docs: List[KnowledgeDocument],
    ) -> List[str]:
        """Return list of ungrounded claim strings."""
        corpus_text = " ".join(
            normalize_text(d.content) for d in existing_docs if d.content
        )
        ungrounded: List[str] = []
        for doc in new_docs:
            claims = self._extract_claims(doc.content)
            for claim in claims:
                if not self._is_grounded(claim, doc.content, corpus_text):
                    ungrounded.append(claim)
        return ungrounded
