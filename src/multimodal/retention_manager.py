"""
Retention Manager for Multimodal Files.

Tracks uploaded files and ensures automatic deletion after the configured
retention period (default 72 hours) or upon retention expiry.
Uses TimeProvider for deterministically testable time calculations.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from src.core.config.settings import get_settings, MultimodalConfig
from src.core.utils.helpers import TimeProvider, get_logger

logger = get_logger("multimodal.retention_manager")


@dataclass
class FileRetentionRecord:
    """Tracks retention metadata for an uploaded file."""
    file_id: str
    filepath: str
    uploaded_at: datetime = field(default_factory=TimeProvider.now)
    expires_at: datetime = field(default_factory=TimeProvider.now)
    is_deleted: bool = False


class RetentionManager:
    """
    Manages retention lifetimes and lifecycle deletion of uploaded customer files.
    """

    def __init__(self, config: Optional[MultimodalConfig] = None) -> None:
        self.config = config or get_settings().multimodal
        self._records: Dict[str, FileRetentionRecord] = {}

    def set_retention(
        self,
        file_id: str,
        filepath: str,
        retention_hours: Optional[int] = None,
    ) -> datetime:
        """
        Record a file for retention tracking and calculate its expiration date.

        Args:
            file_id: Unique identifier of the file/result
            filepath: Absolute or relative path to the stored file
            retention_hours: Optional override for retention period (hours)

        Returns:
            The expiration datetime
        """
        hours = retention_hours if retention_hours is not None else self.config.file_retention_hours
        now = TimeProvider.now()
        expires_at = now + timedelta(hours=hours)

        record = FileRetentionRecord(
            file_id=file_id,
            filepath=filepath,
            uploaded_at=now,
            expires_at=expires_at,
            is_deleted=False,
        )
        self._records[file_id] = record
        logger.info(f"Set retention for file {file_id} ({filepath}) until {expires_at.isoformat()}")
        return expires_at

    def check_expired(self) -> List[str]:
        """
        Return a list of file IDs that have passed their expiration timestamp.
        """
        now = TimeProvider.now()
        expired_ids = []
        for file_id, record in self._records.items():
            if not record.is_deleted and record.expires_at <= now:
                expired_ids.append(file_id)
        return expired_ids

    def cleanup_expired(self) -> int:
        """
        Deletes all expired files from disk and marks records as deleted.

        Returns:
            Count of files deleted.
        """
        expired_ids = self.check_expired()
        deleted_count = 0

        for file_id in expired_ids:
            record = self._records[file_id]
            file_path = Path(record.filepath)
            try:
                if file_path.exists():
                    os.remove(file_path)
                    logger.info(f"Deleted expired file: {file_path}")
                record.is_deleted = True
                deleted_count += 1
            except Exception as e:
                logger.error(f"Failed to delete expired file {file_path}: {e}")

        return deleted_count

    def get_record(self, file_id: str) -> Optional[FileRetentionRecord]:
        """Get retention record for file ID."""
        return self._records.get(file_id)
