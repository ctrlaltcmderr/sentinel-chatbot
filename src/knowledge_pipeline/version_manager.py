"""
Version Manager – stores and retrieves document versions as JSON files,
supporting rollback and version history.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Optional

from ..core.config.settings import get_settings
from ..core.models.data_models import (
    AccessLevel,
    DocumentStatus,
    KnowledgeDocument,
)
from ..core.utils.helpers import TimeProvider, get_logger

logger = get_logger("knowledge_pipeline.version_manager")


class VersionManager:
    """Manage versioned snapshots of KnowledgeDocument instances."""

    def __init__(self, *, settings=None, versions_directory: Optional[str] = None):
        self._settings = settings or get_settings()
        self._versions_dir = versions_directory or self._settings.knowledge_base.versions_directory
        Path(self._versions_dir).mkdir(parents=True, exist_ok=True)

    # ── public API ────────────────────────────────────────────────

    def save_version(self, doc: KnowledgeDocument) -> int:
        """Save a new version of *doc*.  Returns the assigned version number."""
        versions = self.list_versions(doc.id)
        new_version = (max(versions) + 1) if versions else 1
        doc.version = new_version
        doc.updated_at = TimeProvider.now()

        data = self._doc_to_dict(doc)
        data["_version_timestamp"] = doc.updated_at.isoformat()
        self._write_version_file(doc.id, new_version, data)

        logger.info("Saved version %d for doc %s", new_version, doc.id)
        return new_version

    def get_version(self, doc_id: str, version: int) -> Optional[KnowledgeDocument]:
        """Retrieve a specific version of a document."""
        data = self._read_version_file(doc_id, version)
        if data is None:
            logger.warning("Version %d not found for doc %s", version, doc_id)
            return None
        return self._dict_to_doc(data)

    def get_latest(self, doc_id: str) -> Optional[KnowledgeDocument]:
        """Retrieve the most recent version of a document."""
        versions = self.list_versions(doc_id)
        if not versions:
            return None
        return self.get_version(doc_id, max(versions))

    def rollback(self, doc_id: str, to_version: int) -> KnowledgeDocument:
        """Rollback to *to_version* by saving it as a new version.

        Raises ``ValueError`` if the target version does not exist.
        """
        doc = self.get_version(doc_id, to_version)
        if doc is None:
            raise ValueError(
                f"Cannot rollback: version {to_version} not found for doc {doc_id}"
            )
        # Save the rolled-back content as a brand-new version
        new_version = self.save_version(doc)
        logger.info(
            "Rolled back doc %s from version %d -> new version %d",
            doc_id,
            to_version,
            new_version,
        )
        return doc

    def list_versions(self, doc_id: str) -> List[int]:
        """List all stored version numbers for *doc_id*, sorted ascending."""
        doc_dir = self._doc_dir(doc_id)
        if not doc_dir.exists():
            return []
        versions: List[int] = []
        for fname in os.listdir(doc_dir):
            if fname.startswith("v") and fname.endswith(".json"):
                try:
                    versions.append(int(fname[1:].replace(".json", "")))
                except ValueError:
                    continue
        return sorted(versions)

    # ── internal helpers ──────────────────────────────────────────

    def _doc_dir(self, doc_id: str) -> Path:
        return Path(self._versions_dir) / doc_id

    def _version_path(self, doc_id: str, version: int) -> Path:
        return self._doc_dir(doc_id) / f"v{version}.json"

    def _write_version_file(self, doc_id: str, version: int, data: dict) -> None:
        path = self._version_path(doc_id, version)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, default=str)

    def _read_version_file(self, doc_id: str, version: int) -> Optional[dict]:
        path = self._version_path(doc_id, version)
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)

    @staticmethod
    def _doc_to_dict(doc: KnowledgeDocument) -> dict:
        """Serialise a KnowledgeDocument to a plain dict."""
        data = asdict(doc)
        # Enum serialisation
        data["access_level"] = doc.access_level.value
        data["status"] = doc.status.value
        # Datetime serialisation
        for key in ("created_at", "updated_at", "effective_date", "expiry_date"):
            val = data.get(key)
            if val is not None and not isinstance(val, str):
                data[key] = val.isoformat() if hasattr(val, "isoformat") else str(val)
        return data

    @staticmethod
    def _dict_to_doc(data: dict) -> KnowledgeDocument:
        """Deserialise a dict back into a KnowledgeDocument."""
        from datetime import datetime

        data.pop("_version_timestamp", None)

        # Enum deserialisation
        if isinstance(data.get("access_level"), str):
            data["access_level"] = AccessLevel(data["access_level"])
        if isinstance(data.get("status"), str):
            data["status"] = DocumentStatus(data["status"])

        # Datetime deserialisation
        for key in ("created_at", "updated_at", "effective_date", "expiry_date"):
            val = data.get(key)
            if isinstance(val, str):
                try:
                    data[key] = datetime.fromisoformat(val)
                except (ValueError, TypeError):
                    data[key] = None

        return KnowledgeDocument(**data)
