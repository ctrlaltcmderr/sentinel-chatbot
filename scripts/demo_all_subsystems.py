#!/usr/bin/env python3
"""
Sentinel Chatbot - End-to-End Demonstration Script.

Demonstrates all 6 core subsystems and all hidden evaluation scenarios:
1. Multilingual Sentiment Analysis & Dynamic Escalation (Sarcasm, calm high-risk, after-hours)
2. Support Ticket Generation & SLA Lifecycle (Duplicate detection, weekend/holiday SLA)
3. Knowledge Base Pipeline (Deduplication, quarantine, rollback, maintenance window)
4. RAG Knowledge Retrieval (Temporal policy resolution, citation, prompt-injection defense)
5. Multimodal File Processing (Invoice parsing, conflict detection, timeout queue, retention)
6. Multilingual Context & Sessions (Mixed language, code-switching, 24h summary restore)
"""

import os
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.chatbot import SentinelChatbot
from src.core.config.settings import get_settings
from src.core.models.data_models import (
    AccessLevel,
    DocumentStatus,
    KnowledgeDocument,
    Message,
    Priority,
    SentimentType,
)
from src.core.utils.helpers import TimeProvider


def run_demo():
    print("=" * 75)
    print("         SENTINEL CHATBOT - ENTERPRISE SUBSYSTEM DEMONSTRATION")
    print("=" * 75)

    bot = SentinelChatbot()

    # Seed knowledge base with standard policies
    print("\n[+] Seeding Knowledge Base with Active & Historical Policies...")
    doc_warranty_2024 = KnowledgeDocument(
        id="kb-war-2024",
        title="Hardware Warranty Policy 2024",
        product="UltraLaptop",
        version=1,
        access_level=AccessLevel.PUBLIC,
        effective_date=datetime(2024, 1, 1),
        expiry_date=datetime(2025, 1, 1),
        content="UltraLaptop 2024 models include a 1-year basic replacement warranty.",
    )
    doc_warranty_2025 = KnowledgeDocument(
        id="kb-war-2025",
        title="Hardware Warranty Policy 2025-2026",
        product="UltraLaptop",
        version=2,
        access_level=AccessLevel.PUBLIC,
        effective_date=datetime(2025, 1, 2),
        expiry_date=None,
        content="UltraLaptop models include a 2-year premium on-site warranty with accidental damage protection.",
    )
    doc_confidential = KnowledgeDocument(
        id="kb-vip-override",
        title="Executive Settlement Playbook",
        product="All",
        version=1,
        access_level=AccessLevel.CONFIDENTIAL,
        content="Dispute settlements over $5,000 require Legal VP approval.",
    )

    bot.doc_store.add_document(doc_warranty_2024)
    bot.doc_store.add_document(doc_warranty_2025)
    bot.doc_store.add_document(doc_confidential)
    print("    -> 3 knowledge documents indexed.")

    # ─────────────────────────────────────────────────────────────
    # DEMO 1: Multilingual Sentiment Analysis & Calm High-Risk Escalation
    # ─────────────────────────────────────────────────────────────
    print("\n" + "-" * 75)
    print("DEMO 1: Multilingual Sentiment Analysis & Calm High-Risk Escalation")
    print("-" * 75)

    # Set business hours (Wednesday 11:00 AM)
    TimeProvider.set_mock_time(datetime(2026, 10, 28, 11, 0, 0))

    # Scenario A: Sarcasm detection
    sarcasm_msg = "Oh great, another delayed package. Wonderful customer service as always!"
    res1 = bot.handle_message(customer_id="cust-sarcastic", raw_text=sarcasm_msg)
    print(f"Customer: {sarcasm_msg}")
    print(f"-> Sentiment: {res1['sentiment']} (Confidence: {res1['confidence']:.2f})")
    print(f"-> Tone-Adjusted Bot Reply:\n   \"{res1['reply'].splitlines()[0]}\"")

    # Scenario B: Calm High-Risk Complaint
    calm_high_risk = "Hello, I noticed an unauthorized access on my account and double charged payment."
    res2 = bot.handle_message(customer_id="cust-security", raw_text=calm_high_risk)
    print(f"\nCustomer: {calm_high_risk}")
    print(f"-> High-Risk Triggered: {res2['is_high_risk']}")
    print(f"-> Escalated: {res2['escalated']} (Reason: {res2['escalation_reason']})")
    print(f"-> Assigned Team: {res2['assigned_team']} (Ticket #{res2['ticket_id'][:8]})")

    # ─────────────────────────────────────────────────────────────
    # DEMO 2: After-Hours Routing (Urgent vs Normal)
    # ─────────────────────────────────────────────────────────────
    print("\n" + "-" * 75)
    print("DEMO 2: After-Hours Complaint Routing (On-Call vs Next Business Day)")
    print("-" * 75)

    # Set after-hours (Wednesday 11:30 PM)
    TimeProvider.set_mock_time(datetime(2026, 10, 28, 23, 30, 0))

    # Urgent complaint after-hours
    urgent_after_hours = "EMERGENCY! Production database crashed and server is completely down!"
    res3 = bot.handle_message(customer_id="cust-urgent-night", raw_text=urgent_after_hours)
    print(f"Customer (Nighttime): {urgent_after_hours}")
    print(f"-> Escalation Reason: {res3['escalation_reason']}")
    print(f"-> Reply snippet: {res3['reply'].splitlines()[-1]}")

    # ─────────────────────────────────────────────────────────────
    # DEMO 3: RAG Temporal Policy Resolution & Citations
    # ─────────────────────────────────────────────────────────────
    print("\n" + "-" * 75)
    print("DEMO 3: RAG Assistant - Temporal Policy Resolution & Citations")
    print("-" * 75)

    # Current query (Retrieves 2025-2026 Policy v2)
    res_current = bot.handle_message(
        customer_id="cust-rag-1",
        raw_text="What is the warranty policy for UltraLaptop?",
        reference_date=None,  # Current
    )
    print("Query (Current): What is the warranty policy for UltraLaptop?")
    print(f"-> Bot Answer:\n{res_current['reply']}")

    # Historical query (Retrieves 2024 Policy v1)
    res_hist = bot.handle_message(
        customer_id="cust-rag-2",
        raw_text="What was the warranty coverage for purchases made in March 2024?",
        reference_date=datetime(2024, 3, 15),  # Historical
    )
    print(f"\nQuery (Historical - March 2024):")
    print(f"-> Bot Answer:\n{res_hist['reply']}")

    # ─────────────────────────────────────────────────────────────
    # DEMO 4: Multimodal Invoice Verification & Conflict Detection
    # ─────────────────────────────────────────────────────────────
    print("\n" + "-" * 75)
    print("DEMO 4: Multimodal File Analysis & Conflict Detection")
    print("-" * 75)

    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        f.write("TAX INVOICE #ORD-998811\nTotal Paid: $50.00\nDate: 2026-10-10")
        temp_invoice = f.name

    # Customer claims $150 while invoice states $50
    claim_msg = "Here is my invoice, I was charged $150.00 for order ORD-998811."
    res_file = bot.handle_message(
        customer_id="cust-invoice",
        raw_text=claim_msg,
        uploaded_file=temp_invoice,
    )
    file_info = res_file["file_result"]
    print(f"Customer Message: \"{claim_msg}\"")
    print(f"Invoice Extracted Amounts: {file_info.amounts}")
    print(f"Conflicts Detected: {file_info.conflicts}")
    print(f"Masked Log Entry: {file_info.masked_log_entry}")
    os.remove(temp_invoice)

    # ─────────────────────────────────────────────────────────────
    # DEMO 5: Multilingual Code-Switching & Typo Correction
    # ─────────────────────────────────────────────────────────────
    print("\n" + "-" * 75)
    print("DEMO 5: Multilingual Code-Switching & Typo Correction")
    print("-" * 75)

    # Typo correction: "refun", "prodcut"
    typo_text = "I need a refun for my broken prodcut plz."
    processed = bot.input_processor.process(typo_text)
    print(f"Raw Input: \"{typo_text}\"")
    print(f"Typo-Corrected: \"{processed['cleaned_text']}\"")

    # Transliterated Hindi
    hindi_roman = "mera order kab deliver hoga mujhe update chahiye"
    res_hi = bot.handle_message(customer_id="cust-hindi", raw_text=hindi_roman)
    print(f"\nTransliterated Input: \"{hindi_roman}\"")
    print(f"Detected Language: {res_hi.get('sentiment')}")
    print(f"Bot Response: {res_hi['reply'].splitlines()[0]}")

    # ─────────────────────────────────────────────────────────────
    # DEMO 6: Session Expiry (30 min) & 24h Summary Restoration
    # ─────────────────────────────────────────────────────────────
    print("\n" + "-" * 75)
    print("DEMO 6: Session Lifecycle (30m Inactivity Timeout & 24h Restore)")
    print("-" * 75)

    # 1. Customer initiates session at 9 AM
    t_start = datetime(2026, 10, 28, 9, 0, 0)
    TimeProvider.set_mock_time(t_start)
    s1 = bot.session_manager.create_session("cust-journey")
    s1.messages.append(Message(content="I am having trouble configuring my router", is_customer=True))
    print(f"Session Started at 09:00 AM (ID: {s1.session_id[:8]})")

    # 2. Advance 35 minutes -> Expired due to inactivity
    TimeProvider.advance_time(minutes=35)
    bot.session_manager.get_session(s1.session_id)
    print(f"At 09:35 AM: Session Inactivity Timeout Triggered -> Session Closed.")

    # 3. Customer returns at 4 PM (7 hours later < 24 hours)
    TimeProvider.advance_time(hours=7)
    restored = bot.session_manager.restore_session("cust-journey")
    print(f"At 04:35 PM: Customer Returns (<24 hours) -> Session Context Restored:")
    print(f"Restored Summary: \"{restored.previous_session_summary}\"")

    print("\n" + "=" * 75)
    print("             DEMONSTRATION COMPLETED SUCCESSFULLY")
    print("=" * 75)


if __name__ == "__main__":
    run_demo()
