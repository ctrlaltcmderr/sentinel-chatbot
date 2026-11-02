"""
Pipeline Monitor – tracks latency, failures, confidence scores,
escalation counts, and generates alerts.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List, Optional

from ..core.config.settings import get_settings
from ..core.models.data_models import MonitoringMetrics
from ..core.utils.helpers import TimeProvider, get_logger

logger = get_logger("knowledge_pipeline.monitoring")


class PipelineMonitor:
    """Collect metrics and surface alerts for the knowledge pipeline."""

    def __init__(self, *, settings=None):
        self._settings = settings or get_settings()
        mon = self._settings.monitoring
        self._latency_warning_ms = mon.latency_warning_ms
        self._latency_critical_ms = mon.latency_critical_ms
        self._min_confidence = mon.min_confidence_threshold

        self._metrics: List[MonitoringMetrics] = []

    # ── public API ────────────────────────────────────────────────

    def record_metric(self, metric: MonitoringMetrics) -> None:
        """Append a new metrics snapshot."""
        self._metrics.append(metric)
        logger.debug(
            "Metric recorded: component=%s latency=%.0fms confidence=%.2f failures=%d",
            metric.component,
            metric.latency_ms,
            metric.confidence_score,
            metric.failure_count,
        )

    def get_dashboard(self) -> Dict:
        """Return a summary of current system state."""
        if not self._metrics:
            return {
                "total_metrics": 0,
                "avg_latency_ms": 0.0,
                "avg_confidence": 0.0,
                "total_failures": 0,
                "total_escalations": 0,
                "active_sessions": 0,
                "active_tickets": 0,
                "sla_breaches": 0,
            }

        recent = self._recent_metrics(minutes=60)
        if not recent:
            recent = self._metrics[-10:]  # fallback to last 10

        total = len(self._metrics)
        avg_lat = sum(m.latency_ms for m in recent) / len(recent)
        avg_conf = sum(m.confidence_score for m in recent) / len(recent)
        total_fail = sum(m.failure_count for m in self._metrics)
        total_esc = sum(m.escalation_count for m in self._metrics)
        active_sess = recent[-1].active_sessions if recent else 0
        active_tix = recent[-1].active_tickets if recent else 0
        sla = sum(m.sla_breaches for m in self._metrics)

        return {
            "total_metrics": total,
            "avg_latency_ms": round(avg_lat, 2),
            "avg_confidence": round(avg_conf, 3),
            "total_failures": total_fail,
            "total_escalations": total_esc,
            "active_sessions": active_sess,
            "active_tickets": active_tix,
            "sla_breaches": sla,
        }

    def check_alerts(self) -> List[str]:
        """Return a list of active alert messages."""
        alerts: List[str] = []
        recent = self._recent_metrics(minutes=15)
        if not recent:
            return alerts

        # Latency alerts
        avg_lat = sum(m.latency_ms for m in recent) / len(recent)
        if avg_lat > self._latency_critical_ms:
            alerts.append(f"CRITICAL: Average latency {avg_lat:.0f}ms exceeds {self._latency_critical_ms}ms")
        elif avg_lat > self._latency_warning_ms:
            alerts.append(f"WARNING: Average latency {avg_lat:.0f}ms exceeds {self._latency_warning_ms}ms")

        # Confidence alerts
        avg_conf = sum(m.confidence_score for m in recent) / len(recent)
        if avg_conf < self._min_confidence:
            alerts.append(
                f"WARNING: Average confidence {avg_conf:.2f} below threshold {self._min_confidence}"
            )

        # Failure spike
        recent_failures = sum(m.failure_count for m in recent)
        if recent_failures > 5:
            alerts.append(f"WARNING: {recent_failures} failures in last 15 minutes")

        # SLA breaches
        recent_sla = sum(m.sla_breaches for m in recent)
        if recent_sla > 0:
            alerts.append(f"ALERT: {recent_sla} SLA breaches in last 15 minutes")

        for alert in alerts:
            logger.warning(alert)
        return alerts

    # ── internals ─────────────────────────────────────────────────

    def _recent_metrics(self, minutes: int = 15) -> List[MonitoringMetrics]:
        """Return metrics from the last *minutes* minutes."""
        cutoff = TimeProvider.now() - timedelta(minutes=minutes)
        return [m for m in self._metrics if m.timestamp >= cutoff]
