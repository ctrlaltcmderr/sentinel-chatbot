"""
Tests for Component 3: Version Manager.
"""

import tempfile
import unittest

from src.core.models.data_models import KnowledgeDocument
from src.knowledge_pipeline.version_manager import VersionManager


class TestVersionManager(unittest.TestCase):
    """Test document versioning and rollback."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.vm = VersionManager(versions_directory=self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_version_save_and_rollback(self):
        doc = KnowledgeDocument(
            id="doc-123",
            title="Shipping Terms",
            content="Version 1 content: Standard shipping takes 5 days.",
        )
        v1 = self.vm.save_version(doc)
        self.assertEqual(v1, 1)

        # Update doc for v2
        doc.content = "Version 2 content: Standard shipping takes 3 days."
        v2 = self.vm.save_version(doc)
        self.assertEqual(v2, 2)

        # Check latest
        latest = self.vm.get_latest("doc-123")
        self.assertIsNotNone(latest)
        self.assertEqual(latest.version, 2)
        self.assertIn("3 days", latest.content)

        # Rollback to v1
        rolled = self.vm.rollback("doc-123", to_version=1)
        self.assertIsNotNone(rolled)
        self.assertIn("5 days", rolled.content)

        # Verify rollback created a new latest version with v1's content
        latest_after_rb = self.vm.get_latest("doc-123")
        self.assertIn("5 days", latest_after_rb.content)


if __name__ == "__main__":
    unittest.main()
