"""
Safety Checker - Validates queries and documents for security threats.

Detects prompt injection attempts, malicious instructions embedded in
documents, and other safety concerns before content is processed.
"""

from __future__ import annotations

import re
from typing import List, Tuple

from ..core.models.data_models import KnowledgeDocument, DocumentStatus
from ..core.utils.helpers import detect_prompt_injection, get_logger


logger = get_logger("rag.safety_checker")


# Additional patterns for document-level safety checks beyond
# the core prompt injection patterns in settings.
_DOCUMENT_MALICIOUS_PATTERNS: List[Tuple[str, str]] = [
    (r"ignore\s+(?:all|prior|previous)\s+rules", "Instruction to ignore rules"),
    (r"ignore\s+prior\s+rules\s+and\s+reveal\s+secrets", "Prompt injection secret extraction"),
    (r"ignora\s+(?:las\s+)?reglas", "Instruction to ignore rules in Spanish"),
    (r"revela\s+(?:instrucciones\s+ocultas|secretos)", "Attempt to extract secret instructions in Spanish"),
    (r"reveal\s+secrets", "Attempt to extract secrets"),
    (r"index\s+it\s+without\s+scanning", "Bypass scanning instruction"),
    (r"write\s+(?:the\s+)?(?:missing\s+)?refund\s+policy.*from\s+what\s+you\s+think", "Fabricate policy instruction"),
    (r"tell\s+me\s+how\s+to\s+hack", "Hacking instruction"),
    (r"approve\s+all\s+(refunds|requests|claims)", "Instruction to approve all items"),
    (r"override\s+(policy|rules|instructions)", "Policy override instruction"),
    (r"act\s+as\s+(a|an|the)\s+", "Role reassignment instruction"),
    (r"pretend\s+(you|to\s+be)", "Pretend/impersonation instruction"),
    (r"do\s+not\s+follow\s+(the|your|any)\s+(rules|instructions|guidelines)",
     "Instruction to not follow rules"),
    (r"reveal\s+(your|the|all)\s+(instructions|prompt|system)",
     "Attempt to extract system prompt"),
    (r"output\s+(your|the)\s+(system|initial)\s+(prompt|instructions|message)",
     "Attempt to extract system prompt"),
    (r"new\s+instruction[s]?\s*:", "Injected new instructions"),
    (r"<\s*script\s*>", "Embedded script tag"),
    (r"javascript\s*:", "Embedded JavaScript"),
    (r"execute\s+(command|code|script)", "Code execution instruction"),
    (r"delete\s+(all|every)\s+(data|records|documents)", "Data deletion instruction"),
    (r"grant\s+(admin|root|full)\s+(access|permission)", "Privilege escalation instruction"),
]


class SafetyChecker:
    """
    Validates queries and documents for prompt injection and other safety threats.

    Uses the shared `detect_prompt_injection` utility for baseline detection
    and adds document-specific checks for malicious content embedded in
    knowledge base entries.
    """

    def __init__(self) -> None:
        # Compile document-level patterns once
        self._compiled_doc_patterns: List[Tuple[re.Pattern, str]] = [
            (re.compile(pattern, re.IGNORECASE), description)
            for pattern, description in _DOCUMENT_MALICIOUS_PATTERNS
        ]

    def check_query(self, query: str) -> Tuple[bool, List[str]]:
        """
        Check a user query for prompt injection attempts.

        Args:
            query: The raw user query string.

        Returns:
            Tuple of (is_safe, list_of_issues).
            is_safe is True if no injection detected.
        """
        if not query or not query.strip():
            return True, []

        is_injection, matched_patterns = detect_prompt_injection(query)

        issues: List[str] = []
        if is_injection:
            issues.append(
                f"Prompt injection detected: {len(matched_patterns)} suspicious pattern(s) found"
            )
            logger.warning(f"Prompt injection detected in query: {query[:100]}...")

        # Additional query-level checks
        additional_issues = self._check_additional_query_patterns(query)
        issues.extend(additional_issues)

        is_safe = len(issues) == 0
        return is_safe, issues

    def check_document(self, doc: KnowledgeDocument) -> Tuple[bool, List[str]]:
        """
        Check a document for malicious content.

        Detects:
        - Prompt injection patterns in document content or title
        - Hidden instructions that could manipulate system behaviour
        - Suspicious embedded commands

        Args:
            doc: The KnowledgeDocument to validate.

        Returns:
            Tuple of (is_safe, list_of_issues).
            is_safe is True if document passes all checks.
        """
        issues: List[str] = []

        # Check title for injection
        if doc.title:
            is_injection, _ = detect_prompt_injection(doc.title)
            if is_injection:
                issues.append(f"Prompt injection detected in document title: '{doc.title}'")

        # Check content for injection using core utility
        if doc.content:
            is_injection, matched = detect_prompt_injection(doc.content)
            if is_injection:
                issues.append(
                    f"Prompt injection detected in document content "
                    f"({len(matched)} pattern(s) matched)"
                )

            # Check for document-specific malicious patterns
            doc_issues = self._check_document_content(doc.content)
            issues.extend(doc_issues)

        # Check tags for injection
        for tag in doc.tags:
            is_injection, _ = detect_prompt_injection(tag)
            if is_injection:
                issues.append(f"Prompt injection detected in tag: '{tag}'")

        is_safe = len(issues) == 0

        if not is_safe:
            logger.warning(
                f"Safety check failed for document '{doc.title}' "
                f"(id={doc.id}): {len(issues)} issue(s)"
            )
        else:
            logger.debug(f"Document '{doc.title}' (id={doc.id}) passed safety check")

        return is_safe, issues

    def _check_additional_query_patterns(self, query: str) -> List[str]:
        """Check for additional suspicious patterns in queries."""
        issues: List[str] = []

        for compiled_pattern, description in self._compiled_doc_patterns:
            if compiled_pattern.search(query):
                issues.append(f"Suspicious query pattern: {description}")

        return issues

    def _check_document_content(self, content: str) -> List[str]:
        """Check document content for embedded malicious instructions."""
        issues: List[str] = []

        for compiled_pattern, description in self._compiled_doc_patterns:
            if compiled_pattern.search(content):
                issues.append(f"Malicious content in document: {description}")

        return issues
