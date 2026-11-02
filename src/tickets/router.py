"""
Ticket Router - Routes tickets to appropriate teams and agents.

Routes tickets based on issue category, agent availability,
business hours, and workload limits.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple

from src.core.models.data_models import SupportTicket
from src.core.config.settings import get_settings
from src.core.utils.helpers import get_logger, TimeProvider


logger = get_logger("ticket_router")


class TicketRouter:
    """Routes support tickets to teams and individual agents."""

    def __init__(self, settings=None):
        self.settings = settings or get_settings()
        self._agent_workloads: Dict[str, int] = {}
        self._agent_availability: Dict[str, bool] = {}

    def route(self, ticket: SupportTicket) -> Tuple[str, str]:
        """
        Route a ticket to the appropriate team and agent.

        Routing logic:
        1. Determine target team from issue_category.
        2. If the target team has no available agents → fallback to 'general'.
        3. Select the agent with the lowest workload who is available
           and under the max workload limit.

        Args:
            ticket: The support ticket to route.

        Returns:
            Tuple of (team_name, agent_id).  agent_id may be empty
            if no agents are available at all.
        """
        config = self.settings.tickets
        teams = config.teams
        max_workload = config.agent_max_workload

        # Determine target team
        target_team = self._resolve_team(ticket.issue_category, teams)

        # Check business hours
        bh_config = self.settings.business_hours
        is_bh = bh_config.is_business_hours(TimeProvider.now())

        # Try to find an available agent on the target team
        agent = self._pick_agent(target_team, teams, max_workload)

        # Fallback to general only if target team had no capacity AND general has an available agent
        if not agent and target_team != "general":
            fallback_agent = self._pick_agent("general", teams, max_workload)
            if fallback_agent:
                logger.info(
                    "No available agents on team '%s'; falling back to 'general'.",
                    target_team,
                )
                target_team = "general"
                agent = fallback_agent

        if not is_bh:
            ticket.metadata["after_hours"] = True
            ticket.metadata["business_hours"] = False
        else:
            ticket.metadata["business_hours"] = True

        if agent:
            self._agent_workloads[agent] = self._agent_workloads.get(agent, 0) + 1
            ticket.assigned_team = target_team
            ticket.assigned_agent = agent
            logger.info(
                "Routed ticket %s → team=%s, agent=%s (workload=%d)",
                ticket.id[:8], target_team, agent,
                self._agent_workloads[agent],
            )
        else:
            ticket.assigned_team = target_team
            ticket.assigned_agent = ""
            logger.warning(
                "No available agents for ticket %s (team=%s, after_hours=%s)",
                ticket.id[:8], target_team, not is_bh,
            )

        return target_team, agent or ""

    def get_agent_workload(self, agent: str) -> int:
        """Return current ticket count for the specified agent."""
        return self._agent_workloads.get(agent, 0)

    def set_agent_workload(self, agent: str, workload: int) -> None:
        """Explicitly set an agent's workload."""
        self._agent_workloads[agent] = workload

    def set_agent_availability(self, agent: str, available: bool) -> None:
        """
        Set an agent's availability flag.

        Args:
            agent: Agent identifier.
            available: True if the agent can accept tickets.
        """
        self._agent_availability[agent] = available
        logger.info("Agent %s availability set to %s", agent, available)

    def release_ticket(self, agent: str) -> None:
        """Decrement an agent's workload (e.g. when a ticket is resolved)."""
        if agent in self._agent_workloads and self._agent_workloads[agent] > 0:
            self._agent_workloads[agent] -= 1

    # ──────────────────────── Private helpers ────────────────────────

    def _resolve_team(self, category: str, teams: Dict[str, List[str]]) -> str:
        """Map an issue category to a team name."""
        if category in teams:
            return category
        # Try a fuzzy match
        category_lower = category.lower().replace(" ", "_")
        for team_name in teams:
            if team_name in category_lower or category_lower in team_name:
                return team_name
        return "general"

    def _pick_agent(
        self,
        team: str,
        teams: Dict[str, List[str]],
        max_workload: int,
    ) -> Optional[str]:
        """
        Pick the best available agent from a team.

        Selects the agent with the lowest workload who is:
        - marked available (or not explicitly unavailable)
        - below the max workload limit
        """
        agents = teams.get(team, [])
        if not agents:
            return None

        # Check business hours — if outside business hours, only
        # agents explicitly marked available are eligible
        bh_config = self.settings.business_hours
        is_bh = bh_config.is_business_hours(TimeProvider.now())

        candidates: List[Tuple[str, int]] = []
        for agent in agents:
            # Availability: default True during business hours, False outside
            explicitly_set = agent in self._agent_availability
            if explicitly_set:
                available = self._agent_availability[agent]
            else:
                available = is_bh

            if not available:
                continue

            workload = self._agent_workloads.get(agent, 0)
            if workload >= max_workload:
                continue

            candidates.append((agent, workload))

        if not candidates:
            return None

        # Pick the one with the lowest workload
        candidates.sort(key=lambda c: c[1])
        return candidates[0][0]
