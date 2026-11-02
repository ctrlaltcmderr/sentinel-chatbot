"""
Tests for Component 6: Context Manager.

Hidden evaluations:
- 10-message context window retention
- Language switching in the same conversation
- Information correction handling ("Actually, my order ID is ORD-456")
"""

import unittest

from src.core.models.data_models import Message
from src.multilingual.context_manager import ContextManager


class TestContextManager(unittest.TestCase):
    """Test multi-turn context retention, language switching, and corrections."""

    def setUp(self):
        self.context = ContextManager(max_context_messages=10)

    def test_context_window_10_messages(self):
        """Retain context for at least 10 messages."""
        sid = "sess-window-test"
        for i in range(15):
            self.context.add_message(sid, Message(content=f"Message {i}", is_customer=True))

        retained = self.context.get_context(sid, max_messages=10)
        self.assertEqual(len(retained), 10)
        self.assertEqual(retained[0].content, "Message 5")
        self.assertEqual(retained[-1].content, "Message 14")

    def test_language_switching_in_conversation(self):
        """Hidden evaluation: Language switching within the same conversation."""
        sid = "sess-lang-switch"
        # Turn 1: English
        self.context.add_message(sid, Message(content="Hello, I need assistance.", language="en"))
        self.assertEqual(self.context.get_latest_language(sid), "en")

        # Turn 2: Switch to Spanish
        self.context.add_message(sid, Message(content="Prefiero hablar en español por favor.", language="es"))
        self.assertEqual(self.context.get_latest_language(sid), "es")

        # Turn 3: Switch to Hindi
        self.context.add_message(sid, Message(content="क्या आप हिंदी में मदद कर सकते हैं?", language="hi"))
        self.assertEqual(self.context.get_latest_language(sid), "hi")

    def test_information_correction_handling(self):
        """Hidden evaluation: Handle corrected information gracefully."""
        sid = "sess-correction"
        self.context.add_message(sid, Message(content="My order number is ORD-111222."))
        entities = self.context.get_tracked_entities(sid)
        self.assertEqual(entities.get("order_id"), "111222")

        # User corrects themselves
        self.context.add_message(sid, Message(content="Actually, my order is ORD-999888, sorry."))
        updated_entities = self.context.get_tracked_entities(sid)
        self.assertEqual(updated_entities.get("order_id"), "999888")


if __name__ == "__main__":
    unittest.main()
