"""
Health Checker – performs post-update health checks and determines
whether an automatic rollback is needed.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Callable, Dict, List, Optional

from ..core.config.settings import get_settings
from ..core.utils.helpers import TimeProvider, get_logger

logger = get_logger("knowledge_pipeline.health_checker")


class HealthChecker:
    """Run post-activation health checks and trigger rollbacks when needed."""

    def __init__(
        self,
        *,
        settings=None,
        doc_count_provider: Optional[Callable[[], int]] = None,
        error_rate_provider: Optional[Callable[[], float]] = None,
        accuracy_provider: Optional[Callable[[], float]] = None,
    ):
        self._settings = settings or get_settings()
        kb = self._settings.knowledge_base
        self._health_window_minutes = kb.health_check_window_minutes
        self._min_accuracy = kb.min_accuracy_threshold

        # Pluggable health probes (default to healthy values)
        self._doc_count_provider = doc_count_provider or (lambda: 100)
        self._error_rate_provider = error_rate_provider or (lambda: 0.0)
        self._accuracy_provider = accuracy_provider or (lambda: 1.0)

        # Track health-check results per update
        self._results: Dict[str, Dict] = {}

    # ── public API ────────────────────────────────────────────────

    def check_post_update(self, update_id: str, activated_at: datetime) -> Dict:
        """Run health checks for an update activated at *activated_at*.

        Returns a dict with health status fields.
        """
        now = TimeProvider.now()
        elapsed = (now - activated_at).total_seconds() / 60.0
        within_window = elapsed <= self._health_window_minutes

        doc_count = self._doc_count_provider()
        error_rate = self._error_rate_provider()
        accuracy = self._accuracy_provider()

        doc_count_ok = doc_count > 0
        error_rate_ok = error_rate < 0.1  # < 10 % error rate
        accuracy_ok = accuracy >= self._min_accuracy

        all_healthy = doc_count_ok and error_rate_ok and accuracy_ok

        result = {
            "update_id": update_id,
            "activated_at": activated_at.isoformat(),
            "checked_at": now.isoformat(),
            "elapsed_minutes": round(elapsed, 2),
            "within_health_window": within_window,
            "checks": {
                "document_count": {"value": doc_count, "ok": doc_count_ok},
                "error_rate": {"value": error_rate, "ok": error_rate_ok},
                "query_accuracy": {"value": accuracy, "ok": accuracy_ok},
            },
            "healthy": all_healthy,
        }
        self._results[update_id] = result
        logger.info(
            "Health check for update %s: healthy=%s (elapsed=%.1f min, within_window=%s)",
            update_id,
            all_healthy,
            elapsed,
            within_window,
        )
        return result

    def should_rollback(self, health_result: Dict) -> bool:
        """Return True when a rollback is warranted.

        A rollback is triggered when:
        - The health check is within the 5-minute window AND
        - At least one health probe reports failure.
        """
        if not health_result.get("within_health_window", False):
            return False
        return not health_result.get("healthy", True)

    def get_result(self, update_id: str) -> Optional[Dict]:
        """Retrieve the latest health-check result for an update."""
        return self._results.get(update_id)
