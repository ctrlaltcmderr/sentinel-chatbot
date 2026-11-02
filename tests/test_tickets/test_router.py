"""
Tests for Component 2: Ticket Router.

Hidden evaluations:
- Unavailable teams -> fallback to general
- Agent workload limits
- Runtime changes to routing conditions
"""

import unittest

from datetime import datetime

from src.core.config.settings import get_settings
from src.core.models.data_models import SupportTicket
from src.core.utils.helpers import TimeProvider
from src.tickets.router import TicketRouter


class TestTicketRouter(unittest.TestCase):
    """Test ticket routing and fallback mechanisms."""

    def setUp(self):
        self.settings = get_settings()
        self.router = TicketRouter(self.settings)
        # Standard business hours time (Wednesday 11:00 AM)
        TimeProvider.set_mock_time(datetime(2026, 10, 28, 11, 0, 0))

    def tearDown(self):
        TimeProvider.reset()

    def test_standard_team_routing(self):
        ticket = SupportTicket(issue_category="billing")
        team, agent = self.router.route(ticket)
        self.assertEqual(team, "billing")
        self.assertTrue(agent.startswith("billing_agent"))

    def test_unavailable_team_fallback(self):
        """Hidden evaluation: When target team agents are unavailable, fallback to general."""
        # Mark all billing agents unavailable
        self.router.set_agent_availability("billing_agent_1", False)
        self.router.set_agent_availability("billing_agent_2", False)

        ticket = SupportTicket(issue_category="billing")
        team, agent = self.router.route(ticket)
        self.assertEqual(team, "general")
        self.assertTrue(agent.startswith("general_agent"))

    def test_workload_limit_overflow(self):
        """Hidden evaluation: When agents hit max workload limit (10)."""
        # Fill workloads for shipping
        self.router.set_agent_workload("shipping_agent_1", 10)

        ticket = SupportTicket(issue_category="shipping")
        team, agent = self.router.route(ticket)
        # Should fallback to general because shipping is at capacity
        self.assertEqual(team, "general")

    def test_runtime_configuration_changes(self):
        """Hidden evaluation: Dynamic changes to teams at runtime."""
        # Add new emergency team
        self.settings.update_runtime("tickets", "teams", {
            "billing": ["billing_agent_1"],
            "emergency": ["emergency_hero_1"],
            "general": ["general_agent_1"],
        })
        ticket = SupportTicket(issue_category="emergency")
        team, agent = self.router.route(ticket)
        self.assertEqual(team, "emergency")
        self.assertEqual(agent, "emergency_hero_1")

    def test_after_hours_request_no_agent_available(self):
        """Hidden evaluation: After-hours request with no on-call agent retains category and marks after_hours."""
        # Nighttime at 23:30 (outside business hours)
        TimeProvider.set_mock_time(datetime(2026, 10, 28, 23, 30, 0))

        ticket = SupportTicket(issue_category="billing")
        team, agent = self.router.route(ticket)
        self.assertEqual(team, "billing")
        self.assertEqual(agent, "")
        self.assertTrue(ticket.metadata.get("after_hours"))

    def test_after_hours_request_with_on_call_agent(self):
        """Hidden evaluation: After-hours request routes to agent explicitly marked available (on-call)."""
        TimeProvider.set_mock_time(datetime(2026, 10, 28, 23, 30, 0))
        self.router.set_agent_availability("billing_agent_1", True)

        ticket = SupportTicket(issue_category="billing")
        team, agent = self.router.route(ticket)
        self.assertEqual(team, "billing")
        self.assertEqual(agent, "billing_agent_1")
        self.assertTrue(ticket.metadata.get("after_hours"))


if __name__ == "__main__":
    unittest.main()
