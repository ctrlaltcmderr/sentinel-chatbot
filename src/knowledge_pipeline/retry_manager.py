"""
Retry Manager – handles failed knowledge-base updates with configurable
retry intervals, tracking attempts and outcomes.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Callable, Dict, List, Optional

from ..core.config.settings import get_settings
from ..core.utils.helpers import RetryHandler, TimeProvider, get_logger

logger = get_logger("knowledge_pipeline.retry_manager")


class RetryManager(RetryHandler):
    """Manage retries for failed knowledge-base updates.

    Extends :class:`RetryHandler` with update-tracking semantics: each
    failed update gets its own retry state so multiple updates can be
    retried independently.
    """

    def __init__(self, *, settings=None, intervals_minutes: Optional[List[int]] = None):
        s = settings or get_settings()
        intervals = intervals_minutes or s.knowledge_base.retry_intervals_minutes
        super().__init__(intervals_minutes=intervals)
        self._settings = s
        # Per-update tracking: update_id -> state dict
        self._update_states: Dict[str, Dict] = {}

    # ── public API ────────────────────────────────────────────────

    def handle_failed_update(self, update_id: str, error: str) -> Dict:
        """Register (or advance) a failure for *update_id*.

        Returns a dict with retry scheduling info:
        - ``retry_scheduled``: whether another retry will happen
        - ``retry_at``: ISO timestamp of next retry (if any)
        - ``attempt``: current attempt number
        - ``gave_up``: True when all intervals exhausted
        """
        state = self._get_or_create_state(update_id)
        state["attempts"].append({
            "timestamp": TimeProvider.now().isoformat(),
            "error": error,
        })

        attempt_num = len(state["attempts"])
        can_retry = attempt_num <= len(self.intervals)

        if can_retry:
            wait_minutes = self.intervals[attempt_num - 1]
            retry_at = TimeProvider.now() + timedelta(minutes=wait_minutes)
            state["next_retry_at"] = retry_at.isoformat()
            state["gave_up"] = False
            logger.warning(
                "Update %s failed (attempt %d): %s – retrying at %s",
                update_id,
                attempt_num,
                error,
                retry_at.isoformat(),
            )
            return {
                "update_id": update_id,
                "retry_scheduled": True,
                "retry_at": retry_at.isoformat(),
                "wait_minutes": wait_minutes,
                "attempt": attempt_num,
                "gave_up": False,
            }
        else:
            state["next_retry_at"] = None
            state["gave_up"] = True
            logger.error(
                "Update %s failed (attempt %d): %s – giving up after %d retries",
                update_id,
                attempt_num,
                error,
                len(self.intervals),
            )
            return {
                "update_id": update_id,
                "retry_scheduled": False,
                "retry_at": None,
                "wait_minutes": 0,
                "attempt": attempt_num,
                "gave_up": True,
            }

    def get_state(self, update_id: str) -> Optional[Dict]:
        """Return the current retry state for an update, or None."""
        return self._update_states.get(update_id)

    def reset_update(self, update_id: str) -> None:
        """Reset retry state for an update (e.g., after manual resolution)."""
        self._update_states.pop(update_id, None)

    # ── internals ─────────────────────────────────────────────────

    def _get_or_create_state(self, update_id: str) -> Dict:
        if update_id not in self._update_states:
            self._update_states[update_id] = {
                "update_id": update_id,
                "attempts": [],
                "next_retry_at": None,
                "gave_up": False,
            }
        return self._update_states[update_id]
