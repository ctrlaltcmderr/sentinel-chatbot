"""
Document Processor – ingests, validates, deduplicates, and enriches
knowledge documents for the Sentinel Chatbot knowledge base.
"""

from __future__ import annotations

import os
import re
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Set

from ..core.config.settings import get_settings, KnowledgeBaseConfig
from ..core.models.data_models import (
    AccessLevel,
    DocumentStatus,
    KnowledgeDocument,
)
from ..core.utils.helpers import (
    TimeProvider,
    compute_hash,
    detect_prompt_injection,
    generate_id,
    get_logger,
    mask_sensitive_data,
)

logger = get_logger("knowledge_pipeline.document_processor")

# Supported plain-text file extensions for processing
_SUPPORTED_EXTENSIONS: Set[str] = {".txt", ".md", ".json", ".csv", ".html", ".xml", ".yml", ".yaml"}


class DocumentProcessor:
    """Process raw files into validated KnowledgeDocument objects."""

    def __init__(
        self,
        *,
        settings=None,
        known_hashes: Optional[Dict[str, str]] = None,
    ):
        self._settings = settings or get_settings()
        self._kb_config: KnowledgeBaseConfig = self._settings.knowledge_base
        # Map of doc_id -> content_hash for duplicate / change detection
        self._known_hashes: Dict[str, str] = dict(known_hashes or {})
        # Ensure quarantine dir exists
        Path(self._kb_config.quarantine_directory).mkdir(parents=True, exist_ok=True)

    # ── public API ────────────────────────────────────────────────

    def process_document(self, filepath: str) -> Optional[KnowledgeDocument]:
        """Process a single document file.

        Returns a ``KnowledgeDocument`` on success, or ``None`` when the
        file is quarantined, a duplicate, or otherwise skipped.
        """
        filepath = os.path.abspath(filepath)
        logger.info("Processing document: %s", filepath)

        # 1. Validate file existence and extension
        if not self._validate_file(filepath):
            return None

        # 2. Read content
        content = self._read_file(filepath)
        if content is None:
            # read_file already quarantines on error
            return None

        # 3. Check for empty content
        if not content.strip():
            logger.warning("Empty file quarantined: %s", filepath)
            self._quarantine(filepath, reason="empty_file")
            return None

        # 4. Prompt-injection detection
        is_injection, patterns = detect_prompt_injection(content)
        if is_injection:
            logger.warning(
                "Prompt injection detected in %s – patterns: %s",
                filepath,
                patterns,
            )
            self._quarantine(filepath, reason="prompt_injection")
            return None

        # 5. Duplicate / unchanged detection via content hash
        content_hash = compute_hash(content)
        doc_id = self._derive_doc_id(filepath)
        if self._is_duplicate(doc_id, content_hash):
            logger.info("Skipping unchanged document: %s", filepath)
            return None

        # 6. Extract metadata
        title = self._extract_title(filepath, content)
        product = self._extract_product(content)
        region = self._extract_region(content)
        access_level = self._detect_access_level(content)
        tags = self._extract_tags(content)

        # 7. Mask sensitive data
        masked_content = mask_sensitive_data(content)

        # 8. Build document
        now = TimeProvider.now()
        doc = KnowledgeDocument(
            id=doc_id,
            title=title,
            content=masked_content,
            content_hash=content_hash,
            version=1,
            product=product,
            region=region,
            access_level=access_level,
            status=DocumentStatus.ACTIVE,
            source_file=filepath,
            tags=tags,
            created_at=now,
            updated_at=now,
        )

        # 9. Update known hashes
        self._known_hashes[doc_id] = content_hash
        logger.info("Document processed: %s (id=%s)", filepath, doc_id)
        return doc

    def process_batch(self, filepaths: List[str]) -> List[KnowledgeDocument]:
        """Process multiple document files, returning only successfully processed ones."""
        results: List[KnowledgeDocument] = []
        for fp in filepaths:
            doc = self.process_document(fp)
            if doc is not None:
                results.append(doc)
        logger.info(
            "Batch processing complete: %d/%d documents processed",
            len(results),
            len(filepaths),
        )
        return results

    # ── internal helpers ──────────────────────────────────────────

    def _validate_file(self, filepath: str) -> bool:
        """Check file existence and extension support."""
        if not os.path.isfile(filepath):
            logger.error("File not found: %s", filepath)
            return False
        ext = Path(filepath).suffix.lower()
        if ext not in _SUPPORTED_EXTENSIONS:
            logger.warning("Unsupported format '%s', quarantined: %s", ext, filepath)
            self._quarantine(filepath, reason="unsupported_format")
            return False
        return True

    def _read_file(self, filepath: str) -> Optional[str]:
        """Read file content; quarantine on read errors (corrupt)."""
        try:
            with open(filepath, "r", encoding="utf-8") as fh:
                return fh.read()
        except (UnicodeDecodeError, OSError) as exc:
            logger.error("Cannot read file %s: %s", filepath, exc)
            self._quarantine(filepath, reason="corrupt_file")
            return None

    def _quarantine(self, filepath: str, *, reason: str) -> None:
        """Move a file to the quarantine directory."""
        dest_dir = Path(self._kb_config.quarantine_directory)
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / Path(filepath).name
        # Avoid overwrite collisions
        counter = 0
        while dest.exists():
            counter += 1
            stem = Path(filepath).stem
            ext = Path(filepath).suffix
            dest = dest_dir / f"{stem}_{counter}{ext}"
        try:
            shutil.move(filepath, str(dest))
            logger.info("Quarantined %s -> %s (reason: %s)", filepath, dest, reason)
        except OSError as exc:
            logger.error("Failed to quarantine %s: %s", filepath, exc)

    def _is_duplicate(self, doc_id: str, content_hash: str) -> bool:
        """Return True if a document with the same hash is already known."""
        return content_hash in self._known_hashes.values() or self._known_hashes.get(doc_id) == content_hash

    @staticmethod
    def _derive_doc_id(filepath: str) -> str:
        """Derive a deterministic doc_id from the file path."""
        return compute_hash(os.path.abspath(filepath))[:16]

    @staticmethod
    def _extract_title(filepath: str, content: str) -> str:
        """Extract document title from first heading or filename."""
        # Try markdown heading
        match = re.search(r"^#\s+(.+)", content, re.MULTILINE)
        if match:
            return match.group(1).strip()
        # Try XML/HTML title
        match = re.search(r"<title>(.+?)</title>", content, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        # Fallback: filename without extension
        return Path(filepath).stem.replace("_", " ").replace("-", " ").title()

    @staticmethod
    def _extract_product(content: str) -> str:
        """Detect product name from content."""
        match = re.search(
            r"(?:product|service|platform)\s*[:\-–]\s*(.+)",
            content,
            re.IGNORECASE,
        )
        if match:
            return match.group(1).strip().split("\n")[0][:100]
        return ""

    @staticmethod
    def _extract_region(content: str) -> str:
        """Detect region from content."""
        match = re.search(
            r"(?:region|location|geography|market)\s*[:\-–]\s*(.+)",
            content,
            re.IGNORECASE,
        )
        if match:
            return match.group(1).strip().split("\n")[0][:50]
        return ""

    @staticmethod
    def _detect_access_level(content: str) -> AccessLevel:
        """Determine document access level from classification markers."""
        lower = content.lower()
        if "confidential" in lower or "top secret" in lower:
            return AccessLevel.CONFIDENTIAL
        if "restricted" in lower or "need-to-know" in lower:
            return AccessLevel.RESTRICTED
        if "internal" in lower or "staff only" in lower:
            return AccessLevel.INTERNAL
        return AccessLevel.PUBLIC

    @staticmethod
    def _extract_tags(content: str) -> List[str]:
        """Extract tag annotations from content."""
        match = re.search(r"(?:tags|keywords)\s*[:\-–]\s*(.+)", content, re.IGNORECASE)
        if match:
            raw = match.group(1).strip()
            return [t.strip() for t in re.split(r"[,;]", raw) if t.strip()]
        return []
