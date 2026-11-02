"""
Tests for Component 5: Multimodal Processor Orchestration.

Hidden evaluations:
- Delayed processing (>30s) routed to background queue with customer notification
- Low quality image triggers clarification
- Masked logging of customer PII and payment data
"""

import os
import tempfile
import unittest

from src.core.models.data_models import FileProcessingStatus, Message
from src.multimodal.processor import MultimodalProcessor


class TestMultimodalProcessor(unittest.TestCase):
    """Test full multimodal pipeline orchestration and hidden evaluations."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.processor = MultimodalProcessor()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_delayed_processing_routes_to_background_queue(self):
        """Hidden evaluation: If processing exceeds 30s, delegate to background queue and notify customer."""
        sample_file = os.path.join(self.temp_dir.name, "large_doc.txt")
        with open(sample_file, "w") as f:
            f.write("Order #ORD-123456 details.")

        # Simulate 35 seconds of processing time (> 30s threshold)
        result = self.processor.process_file(
            sample_file,
            message=Message(content="Checking status"),
            simulated_duration_seconds=35.0,
        )

        self.assertEqual(result.status, FileProcessingStatus.QUEUED_BACKGROUND)
        self.assertTrue(result.queued_for_background)
        self.assertIn("notification", result.metadata)
        self.assertIn("being processed", result.metadata["notification"])

    def test_pii_masked_in_logs(self):
        """Hidden evaluation: Personal and payment info must be masked in logs."""
        invoice_file = os.path.join(self.temp_dir.name, "receipt.txt")
        with open(invoice_file, "w") as f:
            f.write("Payment by 4111-2222-3333-4444 for order ORD-123456. Email: user@test.com.")

        result = self.processor.process_file(invoice_file)
        self.assertIsNotNone(result.masked_log_entry)
        self.assertNotIn("4111-2222-3333-4444", result.masked_log_entry)
        self.assertIn("***MASKED***", result.masked_log_entry)

    def test_low_quality_blurred_image_requests_clarification(self):
        """Hidden evaluation: Low-quality/blurred image triggers clarification request."""
        # Create a tiny 100-byte image file (triggers quality score < 0.4)
        tiny_image = os.path.join(self.temp_dir.name, "blurred_receipt.png")
        with open(tiny_image, "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

        result = self.processor.process_file(tiny_image)
        self.assertEqual(result.status, FileProcessingStatus.FAILED)
        self.assertLess(result.quality_score, self.processor.config.min_image_quality_score)
        self.assertTrue(result.metadata.get("requires_clarification"))
        self.assertTrue(any("clearer image" in c.lower() for c in result.conflicts))

    def test_mismatched_invoice_requests_clarification(self):
        """Hidden evaluation: Mismatched invoice amount vs customer message triggers conflict & clarification."""
        invoice_file = os.path.join(self.temp_dir.name, "invoice_mismatch.txt")
        with open(invoice_file, "w") as f:
            f.write("Invoice #ORD-778899\nAmount: $200.00\nDate: 2026-10-15")

        customer_msg = Message(content="I was charged $500.00 for order ORD-778899.")
        result = self.processor.process_file(invoice_file, message=customer_msg)

        self.assertTrue(len(result.conflicts) > 0)
        self.assertTrue(result.metadata.get("requires_clarification"))
        self.assertIn("clarification_prompt", result.metadata)


if __name__ == "__main__":
    unittest.main()
