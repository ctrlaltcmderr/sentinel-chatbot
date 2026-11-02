"""
Tests for Component 3: Access Control and Monitoring.
"""

import unittest

from src.core.models.data_models import (
    AccessLevel,
    KnowledgeDocument,
    MonitoringMetrics,
)
from src.knowledge_pipeline.access_control import AccessController
from src.knowledge_pipeline.monitoring import PipelineMonitor


class TestAccessControlAndMonitoring(unittest.TestCase):
    """Test RBAC access permissions, audit logging, and pipeline monitoring."""

    def setUp(self):
        self.ac = AccessController()
        self.monitor = PipelineMonitor()

    def test_access_control_levels(self):
        doc_pub = KnowledgeDocument(id="d1", access_level=AccessLevel.PUBLIC)
        doc_int = KnowledgeDocument(id="d2", access_level=AccessLevel.INTERNAL)
        doc_res = KnowledgeDocument(id="d3", access_level=AccessLevel.RESTRICTED)
        doc_conf = KnowledgeDocument(id="d4", access_level=AccessLevel.CONFIDENTIAL)

        # Public user: can only see public
        self.assertTrue(self.ac.check_access("public", doc_pub))
        self.assertFalse(self.ac.check_access("public", doc_int))
        self.assertFalse(self.ac.check_access("public", doc_res))
        self.assertFalse(self.ac.check_access("public", doc_conf))

        # Staff user: can see public and internal
        self.assertTrue(self.ac.check_access("staff", doc_pub))
        self.assertTrue(self.ac.check_access("staff", doc_int))
        self.assertFalse(self.ac.check_access("staff", doc_res))
        self.assertFalse(self.ac.check_access("staff", doc_conf))

        # Manager user: can see public, internal, restricted
        self.assertTrue(self.ac.check_access("manager", doc_res))
        self.assertFalse(self.ac.check_access("manager", doc_conf))

        # Admin user: can see all
        self.assertTrue(self.ac.check_access("admin", doc_conf))

    def test_audit_logging_unauthorized_access(self):
        """Hidden evaluation: Unauthorized access attempt is blocked and audited."""
        doc_conf = KnowledgeDocument(id="secret-doc", access_level=AccessLevel.CONFIDENTIAL)
        granted = self.ac.check_access("staff", doc_conf)
        self.assertFalse(granted)

        self.ac.audit_access("user-123", "secret-doc", "read", granted)
        log = self.ac.get_audit_log()
        self.assertEqual(len(log), 1)
        self.assertFalse(log[0]["granted"])
        self.assertEqual(log[0]["user_id"], "user-123")

    def test_pipeline_monitoring_metrics(self):
        metric = MonitoringMetrics(
            latency_ms=250.0,
            confidence_score=0.92,
            escalation_count=1,
            failure_count=0,
            component="knowledge_pipeline",
        )
        self.monitor.record_metric(metric)
        dashboard = self.monitor.get_dashboard()
        self.assertEqual(dashboard["total_metrics"], 1)


if __name__ == "__main__":
    unittest.main()
