"""
Tests for Component 2: SLA Manager.

Hidden evaluations:
- SLA calculation excluding weekends and holidays
- 75% warning threshold trigger
- Automatic breach escalation
- Runtime changes to SLA conditions (via settings.update_runtime)
"""

import unittest
from datetime import datetime, timedelta

from src.core.config.settings import get_settings
from src.core.models.data_models import Priority, SupportTicket, TicketStatus
from src.core.utils.helpers import TimeProvider
from src.tickets.sla_manager import SLAManager


class TestSLAManager(unittest.TestCase):
    """Test SLA calculations, warnings, and breach auto-escalation."""

    def setUp(self):
        self.settings = get_settings()
        # Set business hours: 9 AM - 6 PM (9h per day), Mon-Fri
        self.settings.business_hours.weekends = [5, 6]  # Sat, Sun
        self.settings.business_hours.holidays = ["2026-10-29"]  # Thursday holiday
        self.manager = SLAManager(self.settings)
        TimeProvider.reset()

    def tearDown(self):
        TimeProvider.reset()

    def test_sla_excluding_weekends_and_holidays(self):
        """Hidden evaluation: SLA skips weekends and configured holidays."""
        # Ticket created Wednesday 2026-10-28 at 4:00 PM (16:00)
        # Business day ends at 18:00 (2 hours remaining today)
        # Low priority ticket has 24 response business hours
        created = datetime(2026, 10, 28, 16, 0, 0)
        ticket = SupportTicket(priority=Priority.LOW, created_at=created)

        deadline = self.manager.calculate_deadline(ticket)

        # 2h Wed (16:00-18:00)
        # Thu (2026-10-29) is holiday -> 0h
        # Fri (2026-10-30): 9h (09:00-18:00) -> 11h total
        # Sat, Sun: weekends -> 0h
        # Mon (2026-11-02): 9h (09:00-18:00) -> 20h total
        # Tue (2026-11-03): remaining 4h -> 09:00 + 4h = 13:00
        expected = datetime(2026, 11, 3, 13, 0, 0)
        self.assertEqual(deadline, expected)

    def test_sla_75_percent_warning_threshold(self):
        """Hidden evaluation: Generate warning when 75% of allowed time is consumed."""
        # Wednesday 2026-10-28 at 10:00 AM
        created = datetime(2026, 10, 28, 10, 0, 0)
        TimeProvider.set_mock_time(created)

        # High priority ticket has 4.0 business hours SLA
        ticket = SupportTicket(priority=Priority.HIGH, created_at=created)
        self.manager.calculate_deadline(ticket)

        # Advance time by 3.1 business hours -> 3.1 / 4.0 = 77.5% (> 75%)
        TimeProvider.advance_time(hours=3, minutes=6)
        status = self.manager.check_sla_status(ticket)

        self.assertTrue(status["is_warning"])
        self.assertTrue(ticket.sla_warning_sent)
        self.assertFalse(status["is_breached"])

    def test_sla_breach_auto_escalation(self):
        """Hidden evaluation: Automatic escalation upon SLA breach."""
        # Wednesday at 10:00 AM
        created = datetime(2026, 10, 28, 10, 0, 0)
        TimeProvider.set_mock_time(created)

        ticket = SupportTicket(priority=Priority.HIGH, created_at=created)
        self.manager.calculate_deadline(ticket)

        # Advance time by 5 hours (> 4h SLA deadline)
        TimeProvider.advance_time(hours=5)

        is_breached = self.manager.is_breached(ticket)
        self.assertTrue(is_breached)
        self.assertTrue(ticket.sla_breached)
        self.assertEqual(ticket.status, TicketStatus.ESCALATED)

    def test_runtime_changes_to_sla_conditions(self):
        """Hidden evaluation: Runtime changes to SLA conditions affect new calculations."""
        # Change critical response hours from 1.0 to 0.5 hours
        self.settings.update_runtime("sla", "critical_response_hours", 0.5)

        created = datetime(2026, 10, 28, 10, 0, 0)
        ticket = SupportTicket(priority=Priority.CRITICAL, created_at=created)
        deadline = self.manager.calculate_deadline(ticket)

        # 10:00 AM + 30 mins = 10:30 AM
        self.assertEqual(deadline, datetime(2026, 10, 28, 10, 30, 0))


if __name__ == "__main__":
    unittest.main()
