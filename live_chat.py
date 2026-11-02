#!/usr/bin/env python3
"""
Sentinel Chatbot - Interactive Terminal Console.

Allows live interactive testing of all 6 Sentinel subsystems:
- Multilingual sentiment & tone adaptation
- RAG knowledge retrieval with citations
- Automatic high-risk detection & ticket escalation
- Temporal policy resolution
"""

from __future__ import annotations

import logging
import os
import sys
import uuid
from pathlib import Path

# Ensure project root is in sys.path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Handle verbose flag
verbose = "--verbose" in sys.argv or "-v" in sys.argv
if not verbose:
    # Disable informational logs during interactive CLI session
    logging.disable(logging.INFO)



from src.chatbot import SentinelChatbot

SENTIMENT_EMOJIS = {
    "positive": "😊 Positive",
    "neutral": "😐 Neutral",
    "negative": "😡 Negative",
    "frustrated": "😫 Frustrated",
    "urgent": "🚨 Urgent",
    "sarcastic": "😏 Sarcastic",
}


def print_banner():
    print("=" * 65)
    print("           🛡️  SENTINEL CHATBOT - LIVE CONSOLE")
    print("=" * 65)
    print("  Enterprise AI Customer Support Assistant with Live RAG,")
    print("  Multilingual Sentiment, High-Risk Escalation & SLA Tracking.")
    print("=" * 65)
    print("  Commands:")
    print("    /docs     : List active knowledge base documents")
    print("    /tickets  : View tickets created in this session")
    print("    /clear    : Start a fresh customer session")
    print("    exit/quit : Exit the chat session")
    print("=" * 65)


def main():
    print_banner()

    bot = SentinelChatbot()
    customer_id = "customer-" + str(uuid.uuid4())[:8]
    print(f"\n[Session initialized for customer: {customer_id}]")
    print("Sentinel: Hello! How can I assist you today? (Ask about warranty, returns, or billing)\n")

    while True:
        try:
            message = input("You: ").strip()

            if not message:
                continue

            if message.lower() in ["exit", "quit", "q"]:
                print("\nSentinel: Thank you for contacting Sentinel Support. Have a great day!\n")
                break

            if message.lower() == "/docs":
                print("\n--- Active Knowledge Base Documents ---")
                for d in bot.doc_store._documents.values():
                    print(f" • [{d.id}] {d.title} (v{d.version}, Access: {d.access_level.value})")
                print("---------------------------------------\n")
                continue

            if message.lower() == "/tickets":
                print("\n--- Session Support Tickets ---")
                if not bot.tickets:
                    print("  No tickets created yet in this session.")
                else:
                    for t in bot.tickets:
                        print(f" • Ticket #{t.id[:8]} | Priority: {t.priority.value.upper()} | Team: {t.assigned_team} | Status: {t.status.value}")
                print("-------------------------------\n")
                continue

            if message.lower() == "/clear":
                customer_id = "customer-" + str(uuid.uuid4())[:8]
                print(f"\n[Started new session with Customer ID: {customer_id}]\n")
                continue

            result = bot.handle_message(
                customer_id=customer_id,
                raw_text=message,
            )

            sentiment = result.get("sentiment", "neutral")
            sentiment_display = SENTIMENT_EMOJIS.get(sentiment, sentiment.capitalize())
            conf = result.get("confidence", 1.0)
            is_high_risk = result.get("is_high_risk", False)
            escalated = result.get("escalated", False)
            ticket_id = result.get("ticket_id")
            team = result.get("assigned_team")

            print(f"\nSentinel: {result.get('reply')}\n")

            # Telemetry footer
            risk_badge = "🚨 YES" if is_high_risk else "No"
            esc_badge = f"🚨 ESCALATED (Ticket #{ticket_id[:8]} → {team})" if escalated and ticket_id else "No"

            print("┌" + "─" * 45 + "┐")
            print(f"│ Sentiment : {sentiment_display:<32}│")
            print(f"│ Confidence: {conf * 100:>5.1f}%{'':<28}│")
            print(f"│ High Risk : {risk_badge:<32}│")
            print(f"│ Escalation: {esc_badge:<32}│")
            print("└" + "─" * 45 + "┘\n")

        except (EOFError, KeyboardInterrupt):
            print("\nSentinel: Chat session closed. Goodbye!")
            break
        except Exception as e:
            print(f"\n[Error] {str(e)}\n")


if __name__ == "__main__":
    main()
