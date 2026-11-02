"""
Update Scheduler – schedules and executes knowledge-base updates
only during the configured maintenance window.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Callable, Dict, List, Optional

from ..core.config.settings import get_settings
from ..core.models.data_models import KnowledgeDocument
from ..core.utils.helpers import TimeProvider, get_logger

logger = get_logger("knowledge_pipeline.update_scheduler")


class UpdateStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class UpdateScheduler:
    """Schedule and manage knowledge-base update deployments."""

    def __init__(self, *, settings=None, execute_callback: Optional[Callable] = None):
        self._settings = settings or get_settings()
        kb = self._settings.knowledge_base
        self._maint_start = kb.maintenance_window_start_hour
        self._maint_end = kb.maintenance_window_end_hour
        self._schedule_hour = kb.update_schedule_hour
        self._schedule_minute = kb.update_schedule_minute
        # Registered updates: update_id -> metadata dict
        self._updates: Dict[str, Dict] = {}
        # Optional callback invoked when execute_update is called
        self._execute_callback = execute_callback

    # ── public API ────────────────────────────────────────────────

    def schedule_update(self, documents: List[KnowledgeDocument]) -> Dict:
        """Register a batch of documents as a pending update.

        Returns a dict with update metadata (including ``update_id``).
        """
        update_id = str(uuid.uuid4())
        now = TimeProvider.now()
        scheduled_time = now.replace(
            hour=self._schedule_hour,
            minute=self._schedule_minute,
            second=0,
            microsecond=0,
        )
        # If the scheduled time already passed today, push to tomorrow
        if scheduled_time <= now:
            from datetime import timedelta
            scheduled_time += timedelta(days=1)

        entry: Dict = {
            "update_id": update_id,
            "status": UpdateStatus.PENDING.value,
            "documents": [d.id for d in documents],
            "document_objects": documents,
            "scheduled_time": scheduled_time.isoformat(),
            "created_at": now.isoformat(),
            "activated_at": None,
            "error": None,
        }
        self._updates[update_id] = entry
        logger.info(
            "Scheduled update %s with %d documents for %s",
            update_id,
            len(documents),
            scheduled_time.isoformat(),
        )
        return entry

    def is_maintenance_window(self) -> bool:
        """Return True if the current (or mock) time is inside the maintenance window."""
        now = TimeProvider.now()
        return self._maint_start <= now.hour < self._maint_end

    def execute_update(self, update_id: str) -> bool:
        """Execute a scheduled update.

        Returns True on success, False on failure.
        The update will only proceed during the maintenance window.
        """
        entry = self._updates.get(update_id)
        if entry is None:
            logger.error("Update %s not found", update_id)
            return False

        if not self.is_maintenance_window():
            logger.warning(
                "Update %s rejected – outside maintenance window (hour=%d)",
                update_id,
                TimeProvider.now().hour,
            )
            return False

        entry["status"] = UpdateStatus.EXECUTING.value
        logger.info("Executing update %s", update_id)

        try:
            if self._execute_callback is not None:
                self._execute_callback(entry)
            entry["status"] = UpdateStatus.COMPLETED.value
            entry["activated_at"] = TimeProvider.now().isoformat()
            logger.info("Update %s completed successfully", update_id)
            return True
        except Exception as exc:
            entry["status"] = UpdateStatus.FAILED.value
            entry["error"] = str(exc)
            logger.error("Update %s failed: %s", update_id, exc)
            return False

    def get_update(self, update_id: str) -> Optional[Dict]:
        """Retrieve update metadata by ID."""
        return self._updates.get(update_id)

    def mark_failed(self, update_id: str, error: str) -> None:
        """Mark an update as failed externally (e.g., from retry manager)."""
        entry = self._updates.get(update_id)
        if entry:
            entry["status"] = UpdateStatus.FAILED.value
            entry["error"] = error

    def mark_rolled_back(self, update_id: str) -> None:
        """Mark an update as rolled back."""
        entry = self._updates.get(update_id)
        if entry:
            entry["status"] = UpdateStatus.ROLLED_BACK.value
