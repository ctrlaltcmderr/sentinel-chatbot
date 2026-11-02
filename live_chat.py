from src.chatbot import SentinelChatbot
import uuid

print("=" * 55)
print("       SENTINEL CHATBOT - LIVE CHAT")
print("=" * 55)

bot = SentinelChatbot()
customer_id = "customer-" + str(uuid.uuid4())[:8]

print("\nSentinel Chatbot is ready!")
print("Type your message. Type 'exit' to quit.\n")

while True:
    try:
        message = input("You: ").strip()

        if message.lower() in ["exit", "quit"]:
            print("Sentinel: Thank you for contacting support!")
            break

        if not message:
            continue

        result = bot.handle_message(
            customer_id=customer_id,
            raw_text=message
        )

        print("\nSentinel:", result.get("reply"))
        print("\n--- Analysis ---")
        print("Sentiment:", result.get("sentiment"))
        print("Confidence:", result.get("confidence"))
        print("High Risk:", result.get("is_high_risk"))
        print("Escalated:", result.get("escalated"))
        print("Ticket ID:", result.get("ticket_id"))
        print("Assigned Team:", result.get("assigned_team"))
        print("----------------\n")

    except (EOFError, KeyboardInterrupt):
        print("\nSentinel: Chat ended.")
        break
    except Exception as e:
        print("\nError:", str(e))


