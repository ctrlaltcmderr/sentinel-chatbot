import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path

# Ensure project root is in sys.path when running script directly
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.config import CORS_ORIGINS
from backend.database import Base, SessionLocal, engine
from backend.models import ChatMessage, Conversation, DocumentRecord, TicketRecord
from backend.routers import admin, analytics, chat, health, knowledge, tickets
from backend.service import SentinelService

# Configure server logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("sentinel.app")


def seed_initial_demo_data():
    """Seed initial demo conversations, messages, and tickets if DB is empty."""
    db = SessionLocal()
    try:
        service = SentinelService.get_instance()
        service.sync_knowledge_to_db(db)

        # Check if conversations already exist
        if db.query(Conversation).count() == 0:
            logger.info("Database is empty. Seeding initial representative customer conversations and tickets...")
            now = datetime.utcnow()

            # Conversation 1: High-risk account compromise
            c1_id = "sess-sec-901"
            c1 = Conversation(
                id=c1_id,
                customer_id="cust-alex-99",
                customer_name="Alex Mercer",
                title="Unauthorized transaction and account compromise",
                status="escalated",
                last_sentiment="neutral",
                last_confidence=1.0,
                is_high_risk=True,
                escalated=True,
                escalation_reason="high_risk_issue",
                language="en",
                created_at=now - timedelta(hours=3),
                updated_at=now - timedelta(hours=2, minutes=50),
            )
            db.add(c1)

            m1_1 = ChatMessage(
                session_id=c1_id,
                sender="customer",
                content="Hello, I noticed an unauthorized access on my account and double charged payment.",
                timestamp=now - timedelta(hours=3),
                language="en",
                sentiment="neutral",
                confidence=1.0,
                is_high_risk=True,
                escalated=True,
                escalation_reason="high_risk_issue",
            )
            m1_2 = ChatMessage(
                session_id=c1_id,
                sender="sentinel",
                content=(
                    "I understand this is a matter of utmost urgency. Rest assured, your security is our priority.\n\n"
                    "Our security team will immediately suspend active sessions and audit unauthorized charges.\n\n"
                    "[Notice: Your inquiry has been escalated to ACCOUNT_SECURITY (Ticket #tkt-sec-901). Queue: ON_CALL]"
                ),
                timestamp=now - timedelta(hours=2, minutes=59),
                language="en",
                sentiment="neutral",
                confidence=1.0,
                is_high_risk=True,
                escalated=True,
                escalation_reason="high_risk_issue",
            )
            db.add_all([m1_1, m1_2])

            t1 = TicketRecord(
                id="tkt-sec-901",
                session_id=c1_id,
                customer_id="cust-alex-99",
                customer_name="Alex Mercer",
                contact_email="alex.mercer@example.com",
                order_id="ORD-SEC-492",
                product_code="ACC-SECURITY",
                issue_description="Unauthorized transaction and account compromise detected on credit card statement.",
                priority="critical",
                priority_score=0.92,
                status="Escalated",
                assigned_team="account_security",
                assigned_agent="sec_agent_1",
                sla_deadline=now + timedelta(hours=1),
                sla_hours=1.0,
                sla_breached=False,
                escalation_reason="high_risk_issue",
                handoff_summary="Customer reported unauthorized access and duplicate charge. Urgent security audit required.",
                created_at=now - timedelta(hours=2, minutes=59),
                updated_at=now - timedelta(hours=2, minutes=50),
            )
            db.add(t1)

            # Conversation 2: Sarcastic delivery complaint
            c2_id = "sess-sarc-802"
            c2 = Conversation(
                id=c2_id,
                customer_id="cust-sarah-44",
                customer_name="Sarah Connor",
                title="Delayed parcel delivery inquiry",
                status="active",
                last_sentiment="sarcastic",
                last_confidence=0.88,
                is_high_risk=False,
                escalated=False,
                language="en",
                created_at=now - timedelta(hours=5),
                updated_at=now - timedelta(hours=4, minutes=45),
            )
            db.add(c2)

            m2_1 = ChatMessage(
                session_id=c2_id,
                sender="customer",
                content="Oh great, another delayed package. Wonderful customer service as always!",
                timestamp=now - timedelta(hours=5),
                language="en",
                sentiment="sarcastic",
                confidence=0.88,
                is_high_risk=False,
                escalated=False,
            )
            m2_2 = ChatMessage(
                session_id=c2_id,
                sender="sentinel",
                content=(
                    "I recognize your frustration with this situation, and I appreciate you bringing it to our attention. "
                    "Let's work through this systematically to get it resolved. Could you provide your tracking number or order ID?"
                ),
                timestamp=now - timedelta(hours=4, minutes=59),
                language="en",
                sentiment="sarcastic",
                confidence=0.88,
                is_high_risk=False,
                escalated=False,
            )
            db.add_all([m2_1, m2_2])

            # Conversation 3: Standard warranty question
            c3_id = "sess-war-703"
            c3 = Conversation(
                id=c3_id,
                customer_id="cust-david-12",
                customer_name="David Miller",
                title="UltraLaptop warranty policy coverage",
                status="resolved",
                last_sentiment="positive",
                last_confidence=0.92,
                is_high_risk=False,
                escalated=False,
                language="en",
                created_at=now - timedelta(days=1),
                updated_at=now - timedelta(days=1, hours=2),
            )
            db.add(c3)

            m3_1 = ChatMessage(
                session_id=c3_id,
                sender="customer",
                content="What warranty is included with the new UltraLaptop?",
                timestamp=now - timedelta(days=1),
                language="en",
                sentiment="neutral",
                confidence=1.0,
            )
            m3_2 = ChatMessage(
                session_id=c3_id,
                sender="sentinel",
                content=(
                    "UltraLaptop models include a 2-year premium on-site warranty covering hardware defects "
                    "and accidental damage protection with a $0 deductible.\n\n"
                    "Sources:\n- Hardware Warranty Policy 2025-2026 (v2, Effective: 2025-01-01)"
                ),
                timestamp=now - timedelta(days=1),
                language="en",
                sentiment="positive",
                confidence=0.92,
            )
            db.add_all([m3_1, m3_2])

            # Conversation 4: Billing dispute
            t2 = TicketRecord(
                id="tkt-bill-404",
                session_id=None,
                customer_id="cust-elena-55",
                customer_name="Elena Rostova",
                contact_email="elena.r@example.com",
                order_id="ORD-998811",
                product_code="BILL-REFUND",
                issue_description="Invoice mismatch: charged $150.00 while agreement states $50.00.",
                priority="high",
                priority_score=0.78,
                status="In Progress",
                assigned_team="billing",
                assigned_agent="billing_agent_1",
                sla_deadline=now + timedelta(hours=3),
                sla_hours=4.0,
                sla_breached=False,
                escalation_reason="invoice_discrepancy",
                handoff_summary="Customer provided invoice with mismatched figures. Credit adjustment pending review.",
                created_at=now - timedelta(hours=1),
                updated_at=now - timedelta(minutes=20),
            )
            db.add(t2)

            db.commit()
            logger.info("Demo data seeded successfully.")
    except Exception as e:
        logger.error("Error seeding initial data: %s", str(e))
        db.rollback()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create DB schema and seed data
    logger.info("Initializing database schema...")
    Base.metadata.create_all(bind=engine)
    seed_initial_demo_data()
    yield
    # Shutdown logic if any
    logger.info("Shutting down Sentinel Chatbot API...")


app = FastAPI(
    title="Sentinel Chatbot Enterprise API",
    description="Production-grade AI customer support platform with real-time sentiment, SLA, RAG, and multimodal processing.",
    version="2.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routers
app.include_router(health.router)
app.include_router(chat.router)
app.include_router(tickets.router)
app.include_router(knowledge.router)
app.include_router(analytics.router)
app.include_router(admin.router)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Sanitize internal errors to prevent stack trace leaks to customers."""
    logger.error("Unhandled exception processing %s: %s", request.url.path, str(exc), exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "An internal server error occurred. Support teams have been notified."},
    )


# Optionally mount built frontend static files if available
FRONTEND_DIST = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")
if os.path.isdir(FRONTEND_DIST):
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    from backend.config import HOST, PORT

    print("=" * 60)
    print("   SENTINEL CHATBOT - ENTERPRISE BACKEND SERVER")
    print(f"   API Server : http://{HOST}:{PORT}")
    print(f"   Swagger UI : http://{HOST}:{PORT}/docs")
    print(f"   Web App    : http://{HOST}:{PORT}/")
    print("=" * 60)
    uvicorn.run("backend.main:app", host=HOST, port=PORT, reload=True)


