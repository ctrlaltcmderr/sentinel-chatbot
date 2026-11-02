"""
Tests for Component 5: Data Extractor.
"""

import unittest

from src.core.models.data_models import Message
from src.multimodal.data_extractor import DataExtractor


class TestDataExtractor(unittest.TestCase):
    """Test structured extraction, cross-referencing, and conflict detection."""

    def setUp(self):
        self.extractor = DataExtractor()

    def test_structured_data_extraction(self):
        text = (
            "TAX INVOICE\n"
            "Order ID: ORD-998877\n"
            "Date: 2026-10-15\n"
            "Product SKU: SKU-LAPTOP-01\n"
            "Total Amount: $1,250.00\n"
            "Status Error: ERROR-404-NET"
        )
        result = self.extractor.extract(text)
        self.assertIn("998877", result.order_ids)
        self.assertIn("2026-10-15", result.dates)
        self.assertTrue(any("1,250" in a or "1250" in a for a in result.amounts))
        self.assertIn("LAPTOP", result.product_info[0])
        self.assertIn("404", result.error_codes[0])

    def test_never_invent_missing_values(self):
        """Fields not present in the document must remain empty."""
        text = "Just a short note with no invoice details."
        result = self.extractor.extract(text)
        self.assertEqual(result.order_ids, [])
        self.assertEqual(result.dates, [])
        self.assertEqual(result.amounts, [])
        self.assertEqual(result.error_codes, [])

    def test_mismatched_invoice_conflict_detection(self):
        """Hidden evaluation: Mismatched invoice amount vs customer message is flagged."""
        # Document says $50.00
        doc_text = "Receipt for Order #ORD-554433. Total paid: $50.00 on 2026-09-01."
        # Customer claims they were charged $150.00
        msg = Message(content="I was charged $150.00 for order ORD-554433.")

        result = self.extractor.extract(doc_text, message=msg)
        self.assertTrue(len(result.conflicts) > 0)
        self.assertTrue(any("amount" in c.lower() or "conflict" in c.lower() or "differ" in c.lower() for c in result.conflicts))


if __name__ == "__main__":
    unittest.main()
