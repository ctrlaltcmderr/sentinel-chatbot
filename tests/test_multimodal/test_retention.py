"""
Tests for Component 5: File Retention and Cleanup.

Hidden evaluations:
- Automatic cleanup of files past retention period (72 hours)
- TimeProvider simulation of retention lifecycle
"""

import os
import tempfile
import unittest
from datetime import datetime, timedelta

from src.core.utils.helpers import TimeProvider
from src.multimodal.retention_manager import RetentionManager


class TestRetentionManager(unittest.TestCase):
    """Test retention schedule and automatic deletion of expired files."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.manager = RetentionManager()
        TimeProvider.reset()

    def tearDown(self):
        TimeProvider.reset()
        self.temp_dir.cleanup()

    def test_retention_expiry_and_cleanup(self):
        """Hidden evaluation: Files must be deleted after the retention period."""
        start_time = datetime(2026, 10, 28, 10, 0, 0)
        TimeProvider.set_mock_time(start_time)

        # Create temporary file
        file_path = os.path.join(self.temp_dir.name, "upload_test.png")
        with open(file_path, "w") as f:
            f.write("image bytes dummy")

        self.assertTrue(os.path.exists(file_path))

        # Set 72-hour retention
        expiry = self.manager.set_retention("file-001", file_path, retention_hours=72)
        self.assertEqual(expiry, start_time + timedelta(hours=72))

        # After 48 hours: Should NOT be expired
        TimeProvider.advance_time(hours=48)
        self.assertEqual(self.manager.check_expired(), [])
        deleted = self.manager.cleanup_expired()
        self.assertEqual(deleted, 0)
        self.assertTrue(os.path.exists(file_path))

        # After another 30 hours (total 78 hours > 72 hours): Expired!
        TimeProvider.advance_time(hours=30)
        expired_files = self.manager.check_expired()
        self.assertIn("file-001", expired_files)

        # Run cleanup
        deleted = self.manager.cleanup_expired()
        self.assertEqual(deleted, 1)
        self.assertFalse(os.path.exists(file_path))


if __name__ == "__main__":
    unittest.main()
