"""
SLA Manager - Calculates deadlines, checks status, and manages SLA breaches.

All calculations respect business hours, weekends, and holidays as
configured in BusinessHoursConfig.  Uses TimeProvider for the current
time so that tests can inject mock times.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, Optional

from src.core.models.data_models import (
    EscalationReason,
    Priority,
    SupportTicket,
    TicketStatus,
)
from src.core.config.settings import get_settings
from src.core.utils.helpers import (
    calculate_business_hours_elapsed,
    get_logger,
    TimeProvider,
)


logger = get_logger("sla_manager")


class SLAManager:
    """Manages SLA deadlines, warnings, and breach detection."""

    def __init__(self, settings=None):
        self.settings = settings or get_settings()

    # ──────────────────── Public API ────────────────────

    def calculate_deadline(self, ticket: SupportTicket) -> datetime:
        """
        Calculate the SLA deadline for a ticket, excluding weekends
        and configured holidays.

        The SLA response hours are determined by ticket priority.
        The deadline is computed by adding *business hours* from the
        ticket's creation time.

        Args:
            ticket: The support ticket.

        Returns:
            The deadline datetime (naive UTC).
        """
        sla = self.settings.sla
        bh = self.settings.business_hours

        response_hours = self._get_response_hours(ticket.priority)
        deadline = self._add_business_hours(
            ticket.created_at, response_hours, bh, sla
        )

        ticket.sla_deadline = deadline
        logger.info(
            "SLA deadline for ticket %s (%s): %s (%.1f biz hours)",
            ticket.id[:8], ticket.priority.value,
            deadline.isoformat(), response_hours,
        )
        return deadline

    def check_sla_status(self, ticket: SupportTicket) -> Dict:
        """
        Check the current SLA status of a ticket.

        Returns a dict with:
        - total_hours: total SLA hours allocated
        - elapsed_hours: business hours elapsed since creation
        - remaining_hours: business hours remaining
        - percentage_used: % of SLA time consumed
        - is_warning: True if ≥ warning_threshold_percent consumed
        - is_breached: True if deadline has passed
        - status: descriptive status string
        """
        sla = self.settings.sla
        now = TimeProvider.now()

        if ticket.sla_deadline is None:
            self.calculate_deadline(ticket)

        total_hours = self._get_response_hours(ticket.priority)
        elapsed = calculate_business_hours_elapsed(
            ticket.created_at, now,
            exclude_weekends=sla.exclude_weekends,
            exclude_holidays=sla.exclude_holidays,
        )
        remaining = max(0.0, total_hours - elapsed)
        pct_used = (elapsed / total_hours * 100) if total_hours > 0 else 100.0

        is_warning = pct_used >= sla.warning_threshold_percent
        is_breached = now >= ticket.sla_deadline if ticket.sla_deadline else False

        # Auto-escalate on breach
        if is_breached and sla.auto_escalate_on_breach:
            self._auto_escalate(ticket)

        # Send warning
        if is_warning and not ticket.sla_warning_sent:
            ticket.sla_warning_sent = True
            logger.warning(
                "SLA warning for ticket %s: %.1f%% consumed",
                ticket.id[:8], pct_used,
            )

        status_text = "breached" if is_breached else ("warning" if is_warning else "on_track")

        return {
            "total_hours": total_hours,
            "elapsed_hours": round(elapsed, 2),
            "remaining_hours": round(remaining, 2),
            "percentage_used": round(pct_used, 1),
            "is_warning": is_warning,
            "is_breached": is_breached,
            "status": status_text,
        }

    def is_warning_threshold(self, ticket: SupportTicket) -> bool:
        """Return True when ≥ 75% (or configured threshold) of SLA time is consumed."""
        status = self.check_sla_status(ticket)
        return status["is_warning"]

    def is_breached(self, ticket: SupportTicket) -> bool:
        """Return True when the SLA deadline has passed."""
        if ticket.sla_deadline is None:
            self.calculate_deadline(ticket)
        now = TimeProvider.now()
        breached = now >= ticket.sla_deadline
        if breached:
            self._auto_escalate(ticket)
        return breached

    # ──────────────────── Private helpers ────────────────────

    def _get_response_hours(self, priority: Priority) -> float:
        """Get the SLA response hours for a given priority."""
        sla = self.settings.sla
        return {
            Priority.CRITICAL: sla.critical_response_hours,
            Priority.HIGH: sla.high_response_hours,
            Priority.MEDIUM: sla.medium_response_hours,
            Priority.LOW: sla.low_response_hours,
        }.get(priority, sla.medium_response_hours)

    def _add_business_hours(
        self,
        start: datetime,
        hours: float,
        bh,
        sla,
    ) -> datetime:
        """
        Add a given number of *business hours* to a start time,
        skipping weekends and holidays.

        Returns the resulting datetime.
        """
        remaining = hours
        current = start

        daily_start_h = bh.start_hour
        daily_start_m = bh.start_minute
        daily_end_h = bh.end_hour
        daily_end_m = bh.end_minute
        daily_biz_hours = (daily_end_h - daily_start_h) + (daily_end_m - daily_start_m) / 60.0

        # If starting outside business hours, advance to next business period
        current = self._advance_to_business(current, bh, sla)

        max_iterations = 365  # safety guard
        iterations = 0
        while remaining > 0 and iterations < max_iterations:
            iterations += 1
            date_str = current.strftime("%Y-%m-%d")
            is_weekend = sla.exclude_weekends and current.weekday() in bh.weekends
            is_holiday = sla.exclude_holidays and date_str in bh.holidays

            if is_weekend or is_holiday:
                # Skip to next day
                current = (current + timedelta(days=1)).replace(
                    hour=daily_start_h, minute=daily_start_m, second=0, microsecond=0
                )
                continue

            # How many biz hours left today from current position?
            day_end = current.replace(
                hour=daily_end_h, minute=daily_end_m, second=0, microsecond=0
            )
            avail_today = max(0.0, (day_end - current).total_seconds() / 3600.0)

            if remaining <= avail_today:
                current = current + timedelta(hours=remaining)
                remaining = 0.0
            else:
                remaining -= avail_today
                # Move to next day start
                current = (current + timedelta(days=1)).replace(
                    hour=daily_start_h, minute=daily_start_m, second=0, microsecond=0
                )

        return current

    def _advance_to_business(self, dt: datetime, bh, sla) -> datetime:
        """If dt is outside business hours, advance to the next business start."""
        daily_start = dt.replace(
            hour=bh.start_hour, minute=bh.start_minute, second=0, microsecond=0
        )
        daily_end = dt.replace(
            hour=bh.end_hour, minute=bh.end_minute, second=0, microsecond=0
        )

        date_str = dt.strftime("%Y-%m-%d")
        is_weekend = sla.exclude_weekends and dt.weekday() in bh.weekends
        is_holiday = sla.exclude_holidays and date_str in bh.holidays
        is_before = dt < daily_start
        is_after = dt >= daily_end

        if is_weekend or is_holiday or is_after:
            # Advance to next business day
            next_day = (dt + timedelta(days=1)).replace(
                hour=bh.start_hour, minute=bh.start_minute, second=0, microsecond=0
            )
            max_iter = 365
            i = 0
            while i < max_iter:
                i += 1
                ds = next_day.strftime("%Y-%m-%d")
                wknd = sla.exclude_weekends and next_day.weekday() in bh.weekends
                hol = sla.exclude_holidays and ds in bh.holidays
                if not wknd and not hol:
                    return next_day
                next_day += timedelta(days=1)
            return next_day
        elif is_before:
            return daily_start
        return dt

    def _auto_escalate(self, ticket: SupportTicket) -> None:
        """Mark a ticket as SLA-breached and escalate."""
        if ticket.sla_breached:
            return  # Already handled
        sla = self.settings.sla
        if not sla.auto_escalate_on_breach:
            return
        ticket.sla_breached = True
        ticket.status = TicketStatus.ESCALATED
        ticket.metadata["escalation_reason"] = EscalationReason.SLA_BREACH.value
        logger.warning(
            "SLA BREACHED for ticket %s – auto-escalated", ticket.id[:8],
        )
