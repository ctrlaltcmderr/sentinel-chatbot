"""
Regression tests certifying:
1. Delayed order -> no warranty policy retrieval.
2. Warranty question -> warranty policy retrieval.
3. Refund question -> refund policy retrieval.
4. Unauthorized account access -> high-risk security classification.
5. Unauthorized payment -> appropriate payment-security handling.
6. Account compromise -> security escalation.
7. Duplicate payment -> payment-related risk handling.
8. No relevant knowledge document -> safe fallback.
9. Calmly worded security incident -> still detected as high risk.
10. Frustrated customer -> correct sentiment classification.
"""

import unittest
from src.chatbot import SentinelChatbot
from src.core.models.data_models import Priority


class TestRiskAndRAGRegression(unittest.TestCase):
    def setUp(self):
        self.bot = SentinelChatbot()

    def test_case_1_delayed_order_no_warranty_retrieval(self):
        """1. Delayed order -> no warranty policy retrieval."""
        res = self.bot.handle_message(
            customer_id="cust-reg-1",
            raw_text="Where is my order? It was supposed to arrive yesterday.",
        )
        # Must NOT return warranty info
        self.assertNotIn("warranty", res["reply"].lower())
        self.assertNotIn("UltraLaptop", res["reply"])
        for src in res["sources"]:
            self.assertNotEqual(src["document_id"], "kb-war-2025")
            self.assertNotEqual(src["document_id"], "kb-war-2024")
        # Must address order inquiry
        self.assertIn("order", res["reply"].lower())

    def test_case_2_warranty_question_retrieval(self):
        """2. Warranty question -> warranty policy retrieval."""
        res = self.bot.handle_message(
            customer_id="cust-reg-2",
            raw_text="What is the warranty coverage for UltraLaptop?",
        )
        self.assertIn("warranty", res["reply"].lower())
        self.assertIn("UltraLaptop", res["reply"])
        source_ids = [s["document_id"] for s in res["sources"]]
        self.assertIn("kb-war-2025", source_ids)

    def test_case_3_refund_question_retrieval(self):
        """3. Refund question -> refund policy retrieval."""
        res = self.bot.handle_message(
            customer_id="cust-reg-3",
            raw_text="Can I return my item within 30 days for a full refund?",
        )
        self.assertIn("30 days", res["reply"].lower())
        self.assertIn("refund", res["reply"].lower())
        source_ids = [s["document_id"] for s in res["sources"]]
        self.assertIn("kb-ret-2026", source_ids)
        self.assertNotIn("kb-war-2025", source_ids)

    def test_case_4_unauthorized_account_access_high_risk(self):
        """4. Unauthorized account access -> high-risk security classification."""
        res = self.bot.handle_message(
            customer_id="cust-reg-4",
            raw_text="Someone accessed my account without permission.",
        )
        self.assertTrue(res["is_high_risk"])
        self.assertEqual(res["risk_category"], "account_compromise")
        self.assertEqual(res["risk_level"], "critical")
        self.assertTrue(res["escalated"])

    def test_case_5_unauthorized_payment_handling(self):
        """5. Unauthorized payment -> appropriate payment-security handling."""
        res = self.bot.handle_message(
            customer_id="cust-reg-5",
            raw_text="I noticed an unauthorized payment on my bank statement.",
        )
        self.assertTrue(res["is_high_risk"])
        self.assertIn(res["risk_category"], {"unauthorized_payment", "account_compromise"})
        # Must never return generic retail return policy
        source_ids = [s["document_id"] for s in res["sources"]]
        self.assertNotIn("kb-ret-2026", source_ids)
        self.assertNotIn("kb-war-2025", source_ids)

    def test_case_6_account_compromise_security_escalation(self):
        """6. Account compromise -> security escalation and routing to account_security."""
        res = self.bot.handle_message(
            customer_id="cust-reg-6",
            raw_text="Someone accessed my account without permission and I noticed an unauthorized payment.",
        )
        self.assertTrue(res["is_high_risk"])
        self.assertTrue(res["escalated"])
        self.assertIsNotNone(res["ticket_id"])
        self.assertEqual(res["assigned_team"], "account_security")
        self.assertIn("ACCOUNT_SECURITY", res["reply"])

        # Check created ticket priority
        ticket = next((t for t in self.bot.tickets if t.id == res["ticket_id"]), None)
        self.assertIsNotNone(ticket)
        self.assertEqual(ticket.priority, Priority.CRITICAL)
        self.assertEqual(ticket.assigned_team, "account_security")

    def test_case_7_duplicate_payment_risk_handling(self):
        """7. Duplicate payment -> payment-related risk handling and billing routing."""
        res = self.bot.handle_message(
            customer_id="cust-reg-7",
            raw_text="I was double charged and charged twice for my subscription order.",
        )
        self.assertTrue(res["is_high_risk"])
        self.assertEqual(res["risk_category"], "duplicate_payment")
        self.assertTrue(res["escalated"])
        self.assertEqual(res["assigned_team"], "billing")

    def test_case_8_no_relevant_knowledge_document_fallback(self):
        """8. No relevant knowledge document -> safe fallback without hallucination."""
        res = self.bot.handle_message(
            customer_id="cust-reg-8",
            raw_text="What is the secret recipe for dark chocolate soufflé?",
        )
        self.assertIn("not have enough verified information", res["reply"])
        self.assertEqual(len(res["sources"]), 0)

    def test_case_9_calmly_worded_security_incident_detected_as_high_risk(self):
        """9. Calmly worded security incident -> still detected as high risk."""
        res = self.bot.handle_message(
            customer_id="cust-reg-9",
            raw_text="Good day, I would like to report that someone logged into my account without permission yesterday. Thank you.",
        )
        self.assertTrue(res["is_high_risk"])
        self.assertEqual(res["risk_category"], "account_compromise")
        self.assertTrue(res["escalated"])
        self.assertEqual(res["assigned_team"], "account_security")

    def test_case_10_frustrated_customer_correct_sentiment(self):
        """10. Frustrated customer -> correct sentiment classification."""
        res = self.bot.handle_message(
            customer_id="cust-reg-10",
            raw_text="I am sick and tired of waiting for days with no response! This is completely ridiculous and unacceptable!",
        )
        self.assertEqual(res["sentiment"], "frustrated")
        self.assertGreaterEqual(res["confidence"], 0.60)


if __name__ == "__main__":
    unittest.main()
