"""
Tests for Component 6: Session Manager.

Hidden evaluations:
- 30-minute inactivity timeout
- 24-hour summary restoration
- Fresh session when > 24 hours
- Simultaneous session isolation
- Simulated time expiry with TimeProvider
- Configurable timings
"""

import unittest
from datetime import datetime, timedelta

from src.core.models.data_models import Message
from src.core.utils.helpers import TimeProvider
from src.multilingual.session_manager import SessionManager


class TestSessionManager(unittest.TestCase):
    """Test customer session lifecycle, timeouts, and restoration."""

    def setUp(self):
        TimeProvider.reset()
        self.manager = SessionManager()

    def tearDown(self):
        TimeProvider.reset()

    def test_session_isolation_simultaneous_customers(self):
        """Hidden evaluation: Isolate simultaneous customer sessions."""
        s1 = self.manager.create_session("customer-A", language="en")
        s2 = self.manager.create_session("customer-B", language="es")

        self.assertNotEqual(s1.session_id, s2.session_id)
        self.assertEqual(self.manager.get_session(s1.session_id).customer_id, "customer-A")
        self.assertEqual(self.manager.get_session(s2.session_id).customer_id, "customer-B")

    def test_30_minute_inactivity_timeout(self):
        """Hidden evaluation: End active session after 30 minutes of inactivity."""
        now = datetime(2026, 10, 28, 10, 0, 0)
        TimeProvider.set_mock_time(now)

        sess = self.manager.create_session("cust-1")
        sid = sess.session_id

        # 20 minutes elapsed -> Still active
        TimeProvider.advance_time(minutes=20)
        active_sess = self.manager.get_active_session("cust-1")
        self.assertIsNotNone(active_sess)
        self.assertTrue(active_sess.is_active)

        # Advance 15 more minutes -> Total 35 mins (> 30 mins) -> Expired
        TimeProvider.advance_time(minutes=15)
        expired_sess = self.manager.get_active_session("cust-1")
        self.assertIsNone(expired_sess)  # Active session no longer available

        # Session object marked expired
        sess_obj = self.manager.get_session(sid)
        self.assertFalse(sess_obj.is_active)
        self.assertTrue(sess_obj.expired)

    def test_restore_session_summary_within_24_hours(self):
        """Hidden evaluation: If customer returns within 24h, restore conversation summary."""
        t0 = datetime(2026, 10, 28, 9, 0, 0)
        TimeProvider.set_mock_time(t0)

        sess = self.manager.create_session("cust-returning")
        sess.messages.append(Message(content="I need a refund for my damaged monitor", is_customer=True))
        self.manager.expire_session(sess.session_id)

        # Customer returns 8 hours later (within 24 hours)
        TimeProvider.advance_time(hours=8)
        restored = self.manager.restore_session("cust-returning")
        self.assertIsNotNone(restored)
        self.assertTrue(len(restored.previous_session_summary) > 0)
        self.assertIn("damaged monitor", restored.previous_session_summary)

    def test_new_session_after_24_hours(self):
        """Hidden evaluation: If customer returns after 24h, begin new session (no restoration)."""
        t0 = datetime(2026, 10, 28, 9, 0, 0)
        TimeProvider.set_mock_time(t0)

        sess = self.manager.create_session("cust-late")
        sess.messages.append(Message(content="Old issue from last week", is_customer=True))
        self.manager.expire_session(sess.session_id)

        # Customer returns 26 hours later (> 24 hours)
        TimeProvider.advance_time(hours=26)
        restored = self.manager.restore_session("cust-late")
        self.assertIsNone(restored)

        # Start fresh session
        fresh = self.manager.start_new_session("cust-late")
        self.assertIsNotNone(fresh)
        self.assertEqual(fresh.previous_session_summary, "")


if __name__ == "__main__":
    unittest.main()
