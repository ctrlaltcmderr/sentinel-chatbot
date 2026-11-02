"""
Support Ticket Management System.

Handles ticket creation, prioritization, routing, SLA management,
duplicate detection, and agent handoff.
"""

from .ticket_creator import TicketCreator
from .priority_calculator import PriorityCalculator
from .router import TicketRouter
from .sla_manager import SLAManager
from .duplicate_detector import DuplicateDetector
from .handoff import HandoffManager

__all__ = [
    "TicketCreator",
    "PriorityCalculator",
    "TicketRouter",
    "SLAManager",
    "DuplicateDetector",
    "HandoffManager",
]
