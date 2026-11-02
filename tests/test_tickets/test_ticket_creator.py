"""
Tests for Component 2: Ticket Creator.
"""

import unittest
from datetime import datetime

from src.core.models.data_models import (
    ConversationContext,
    Message,
    Priority,
    SupportTicket,
    TicketStatus,
)
from src.tickets.ticket_creator import TicketCreator


class TestTicketCreator(unittest.TestCase):
    """Test ticket creation from conversation context and missing info detection."""

    def setUp(self):
        self.creator = TicketCreator()

    def test_complete_ticket_creation(self):
        ctx = ConversationContext(session_id="sess-100", customer_id="cust-100")
        ctx.add_message(Message(content="Hello, my name is John Doe and my email is john@example.com."))
        ctx.add_message(Message(content="I have an issue with order ORD-123456."))
        ctx.add_message(Message(content="The payment of $120.50 was charged twice for product PROD-9988. Here is my screenshot proof."))

        ticket = self.creator.create_from_conversation(ctx)
        self.assertIsInstance(ticket, SupportTicket)
        self.assertEqual(ticket.order_id, "123456")
        self.assertEqual(ticket.customer_email, "john@example.com")
        self.assertIn("John", ticket.customer_name)
        self.assertEqual(len(ticket.missing_fields), 0)

    def test_missing_mandatory_fields_request(self):
        ctx = ConversationContext(session_id="sess-101", customer_id="cust-101")
        # Incomplete conversation: no email, no name
        ctx.add_message(Message(content="The screen is flickering."))

        ticket = self.creator.create_from_conversation(ctx)
        self.assertTrue(len(ticket.missing_fields) > 0)
        self.assertIn("contact_email", ticket.missing_fields)

        request_msg = self.creator.request_missing_info(ticket)
        self.assertIn("email", request_msg.lower())


if __name__ == "__main__":
    unittest.main()
