"""
Tests for Component 3: Update Scheduler, Health Checker, and Retry Manager.

Hidden evaluations:
- Update activates only during maintenance window
- Failed update retry at 15, 30, 60 minutes
- Auto-rollback when health checks fail within 5 minutes
- Simulated maintenance window using TimeProvider
"""

import unittest
from datetime import datetime, timedelta

from src.core.models.data_models import KnowledgeDocument
from src.core.utils.helpers import TimeProvider
from src.knowledge_pipeline.health_checker import HealthChecker
from src.knowledge_pipeline.retry_manager import RetryManager
from src.knowledge_pipeline.update_scheduler import UpdateScheduler, UpdateStatus


class TestUpdateSchedulerAndHealth(unittest.TestCase):
    """Test maintenance windows, execution, health checking, and retries."""

    def setUp(self):
        self.scheduler = UpdateScheduler()
        self.retry_manager = RetryManager()
        TimeProvider.reset()

    def tearDown(self):
        TimeProvider.reset()

    def test_maintenance_window_enforcement(self):
        """Hidden evaluation: Activate approved updates only during maintenance window (1 AM - 5 AM)."""
        doc = KnowledgeDocument(title="Test Doc", content="Content")
        update = self.scheduler.schedule_update([doc])
        update_id = update["update_id"]

        # 1. Daytime (2 PM): Should reject execution
        day_time = datetime(2026, 10, 28, 14, 0, 0)
        TimeProvider.set_mock_time(day_time)
        self.assertFalse(self.scheduler.is_maintenance_window())
        success = self.scheduler.execute_update(update_id)
        self.assertFalse(success)

        # 2. Simulated Maintenance Window (2 AM): Should succeed
        night_time = datetime(2026, 10, 29, 2, 0, 0)
        TimeProvider.set_mock_time(night_time)
        self.assertTrue(self.scheduler.is_maintenance_window())
        success_night = self.scheduler.execute_update(update_id)
        self.assertTrue(success_night)

    def test_retry_intervals_15_30_60_minutes(self):
        """Hidden evaluation: Retries at 15, 30, and 60 minutes."""
        now = datetime(2026, 10, 28, 2, 0, 0)
        TimeProvider.set_mock_time(now)

        update_id = "failed-update-1"

        # Attempt 1 -> 15 min wait
        r1 = self.retry_manager.handle_failed_update(update_id, "Network timeout")
        self.assertTrue(r1["retry_scheduled"])
        self.assertEqual(r1["attempt"], 1)
        expected_retry_1 = (now + timedelta(minutes=15)).isoformat()
        self.assertEqual(r1["retry_at"], expected_retry_1)

        # Attempt 2 -> 30 min wait
        TimeProvider.set_mock_time(now + timedelta(minutes=15))
        r2 = self.retry_manager.handle_failed_update(update_id, "Connection refused")
        self.assertTrue(r2["retry_scheduled"])
        self.assertEqual(r2["attempt"], 2)
        expected_retry_2 = (TimeProvider.now() + timedelta(minutes=30)).isoformat()
        self.assertEqual(r2["retry_at"], expected_retry_2)

        # Attempt 3 -> 60 min wait
        TimeProvider.set_mock_time(now + timedelta(minutes=45))
        r3 = self.retry_manager.handle_failed_update(update_id, "Database lock")
        self.assertTrue(r3["retry_scheduled"])
        self.assertEqual(r3["attempt"], 3)
        expected_retry_3 = (TimeProvider.now() + timedelta(minutes=60)).isoformat()
        self.assertEqual(r3["retry_at"], expected_retry_3)

        # Attempt 4 -> Exhausted / gave up
        TimeProvider.set_mock_time(now + timedelta(minutes=105))
        r4 = self.retry_manager.handle_failed_update(update_id, "Fatal crash")
        self.assertFalse(r4["retry_scheduled"])
        self.assertTrue(r4["gave_up"])

    def test_auto_rollback_on_health_check_failure_within_5_minutes(self):
        """Hidden evaluation: Auto-rollback if health checks fail within 5 minutes of activation."""
        activated_at = datetime(2026, 10, 28, 2, 0, 0)
        TimeProvider.set_mock_time(activated_at + timedelta(minutes=3))  # 3 mins in (within 5 min window)

        # Healthy checker
        healthy_checker = HealthChecker(
            doc_count_provider=lambda: 50,
            error_rate_provider=lambda: 0.01,
            accuracy_provider=lambda: 0.95,
        )
        res_healthy = healthy_checker.check_post_update("up-1", activated_at)
        self.assertFalse(healthy_checker.should_rollback(res_healthy))

        # Faulty checker (error spike / service outage)
        unhealthy_checker = HealthChecker(
            doc_count_provider=lambda: 50,
            error_rate_provider=lambda: 0.40,  # 40% error rate!
            accuracy_provider=lambda: 0.60,
        )
        res_unhealthy = unhealthy_checker.check_post_update("up-2", activated_at)
        self.assertTrue(unhealthy_checker.should_rollback(res_unhealthy))


if __name__ == "__main__":
    unittest.main()
