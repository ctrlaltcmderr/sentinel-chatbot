import json
import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from backend.models import (
    AuditLogRecord,
    ChatMessage,
    Conversation,
    DocumentRecord,
    InternalNoteRecord,
    TicketRecord,
)
from src.chatbot import SentinelChatbot
from src.core.models.data_models import (
    AccessLevel,
    DocumentStatus,
    KnowledgeDocument,
    Priority,
    SupportTicket,
)
from src.core.utils.helpers import TimeProvider

logger = logging.getLogger("sentinel.service")


class SentinelService:
    _instance: Optional["SentinelService"] = None

    def __init__(self) -> None:
        self.bot = SentinelChatbot()
        self.response_latencies: List[float] = []
        self._seed_default_knowledge()
        logger.info("SentinelService initialized with core Chatbot engine.")

    @classmethod
    def get_instance(cls) -> "SentinelService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _seed_default_knowledge(self) -> None:
        """Seed foundational knowledge documents into DocumentStore."""
        docs = [
            KnowledgeDocument(
                id="kb-war-2025",
                title="Hardware Warranty Policy 2025-2026",
                product="UltraLaptop",
                region="global",
                access_level=AccessLevel.PUBLIC,
                version=2,
                effective_date=datetime(2025, 1, 1),
                expiry_date=datetime(2026, 12, 31),
                content=(
                    "UltraLaptop models include a 2-year premium on-site warranty covering hardware defects "
                    "and accidental damage protection with a $0 deductible."
                ),
            ),
            KnowledgeDocument(
                id="kb-war-2024",
                title="Hardware Warranty Policy 2024",
                product="UltraLaptop",
                region="global",
                access_level=AccessLevel.PUBLIC,
                version=1,
                effective_date=datetime(2024, 1, 1),
                expiry_date=datetime(2024, 12, 31),
                content=(
                    "UltraLaptop 2024 models include a 1-year basic replacement warranty covering manufacturer "
                    "defects only. Accidental liquid and drop damage are not covered under standard terms."
                ),
            ),
            KnowledgeDocument(
                id="kb-ret-2026",
                title="Global Return and Refund Policy",
                product="General",
                region="global",
                access_level=AccessLevel.PUBLIC,
                version=1,
                effective_date=datetime(2025, 6, 1),
                expiry_date=None,
                content=(
                    "Customers may return items within 30 days of delivery for a full refund to the original payment method. "
                    "Items must be in original condition with packaging. Refunds are processed within 3 to 5 business days."
                ),
            ),
            KnowledgeDocument(
                id="kb-sec-2026",
                title="Account Security & Compromise Protocol",
                product="General",
                region="global",
                access_level=AccessLevel.INTERNAL,
                version=1,
                effective_date=datetime(2025, 1, 1),
                expiry_date=None,
                content=(
                    "When an account compromise or unauthorized access is reported, the security team must immediately "
                    "suspend active sessions, initiate password resets, and audit the last 48 hours of transactions."
                ),
            ),
            KnowledgeDocument(
                id="kb-sec-public-2026",
                title="Account Security & Unauthorized Access Policy",
                product="General",
                region="global",
                access_level=AccessLevel.PUBLIC,
                version=1,
                effective_date=datetime(2025, 1, 1),
                expiry_date=None,
                content=(
                    "If you notice unauthorized account access or suspect your account is compromised, "
                    "immediately change your password and notify customer support. Our security team will "
                    "terminate active sessions, secure your account credentials, and investigate all unauthorized actions."
                ),
            ),
            KnowledgeDocument(
                id="kb-fraud-public-2026",
                title="Payment Security & Fraud Protection Policy",
                product="General",
                region="global",
                access_level=AccessLevel.PUBLIC,
                version=1,
                effective_date=datetime(2025, 1, 1),
                expiry_date=None,
                content=(
                    "Customers are fully protected against unauthorized payments and fraudulent charges. If you identify "
                    "an unrecognized charge, report it immediately to our security response team. Verified unauthorized "
                    "transactions are cancelled and refunded in full."
                ),
            ),
            KnowledgeDocument(
                id="kb-ship-public-2026",
                title="Shipping and Delivery Policy",
                product="General",
                region="global",
                access_level=AccessLevel.PUBLIC,
                version=1,
                effective_date=datetime(2025, 1, 1),
                expiry_date=None,
                content=(
                    "Standard delivery takes 3 to 5 business days, and express delivery delivers in 1 to 2 business days. "
                    "To check tracking details, please provide your Order ID. If an order is delayed, support will open a "
                    "carrier delivery investigation."
                ),
            ),
            KnowledgeDocument(
                id="kb-settle-playbook",
                title="Executive Settlement Playbook",
                product="All",
                region="global",
                access_level=AccessLevel.CONFIDENTIAL,
                version=1,
                effective_date=datetime(2025, 1, 1),
                expiry_date=None,
                content=(
                    "Authorized directors may settle legal claims up to $100,000 without board approval under strict NDA."
                ),
            ),
        ]
        for doc in docs:
            self.bot.doc_store.add_document(doc)

    def process_message(
        self,
        db: Session,
        customer_id: str,
        message_text: str,
        session_id: Optional[str] = None,
        reference_date: Optional[str] = None,
        user_access_level: str = "public",
        uploaded_file: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Process inbound message through SentinelChatbot, persist in SQLite, and return structured response.
        """
        start_time = time.time()

        # Parse reference date if provided
        ref_dt = None
        if reference_date:
            try:
                ref_dt = datetime.fromisoformat(reference_date.replace("Z", "+00:00"))
            except Exception:
                ref_dt = None

        # Execute existing SentinelChatbot engine
        result = self.bot.handle_message(
            customer_id=customer_id,
            raw_text=message_text,
            reference_date=ref_dt,
            user_access_level=user_access_level,
            uploaded_file=uploaded_file,
        )

        latency_ms = (time.time() - start_time) * 1000
        self.response_latencies.append(latency_ms)
        if len(self.response_latencies) > 200:
            self.response_latencies.pop(0)

        active_session_id = result.get("session_id") or session_id or str(uuid.uuid4())
        now = datetime.utcnow()

        # 1. Update or create Conversation in SQLite
        conv = db.query(Conversation).filter(Conversation.id == active_session_id).first()
        if not conv:
            title = message_text[:40] + ("..." if len(message_text) > 40 else "")
            conv = Conversation(
                id=active_session_id,
                customer_id=customer_id,
                customer_name=f"Customer {customer_id[-4:]}" if len(customer_id) >= 4 else customer_id,
                title=title,
                status="escalated" if result.get("escalated") else "active",
                last_sentiment=result.get("sentiment", "neutral"),
                last_confidence=result.get("confidence", 1.0),
                is_high_risk=result.get("is_high_risk", False),
                escalated=result.get("escalated", False),
                escalation_reason=result.get("escalation_reason"),
                language="en",
                created_at=now,
                updated_at=now,
            )
            db.add(conv)
        else:
            conv.updated_at = now
            conv.last_sentiment = result.get("sentiment", conv.last_sentiment)
            conv.last_confidence = result.get("confidence", conv.last_confidence)
            if result.get("is_high_risk"):
                conv.is_high_risk = True
            if result.get("escalated"):
                conv.escalated = True
                conv.status = "escalated"
                conv.escalation_reason = result.get("escalation_reason")

        # 2. Add customer message to SQLite
        file_info = None
        if result.get("file_result"):
            fr = result["file_result"]
            file_info = {
                "file_path": fr.file_path,
                "file_type": fr.file_type,
                "is_safe": fr.is_safe,
                "status": fr.status.value if hasattr(fr.status, "value") else str(fr.status),
                "extracted_order_ids": fr.extracted_order_ids,
                "extracted_dates": fr.extracted_dates,
                "extracted_amounts": fr.extracted_amounts,
                "conflicts_detected": fr.conflicts_detected,
                "quality_score": fr.quality_score,
            }

        cust_msg = ChatMessage(
            session_id=active_session_id,
            sender="customer",
            content=message_text,
            timestamp=now - timedelta(milliseconds=latency_ms),
            language="en",
            sentiment=result.get("sentiment"),
            confidence=result.get("confidence"),
            is_high_risk=result.get("is_high_risk", False),
            escalated=result.get("escalated", False),
            escalation_reason=result.get("escalation_reason"),
            file_info_json=json.dumps(file_info) if file_info else None,
        )
        db.add(cust_msg)

        # 3. Add bot reply to SQLite (Sentinel response has professional tone, distinct from customer sentiment)
        bot_msg = ChatMessage(
            session_id=active_session_id,
            sender="sentinel",
            content=result.get("reply", ""),
            timestamp=now,
            language="en",
            sentiment="professional",
            confidence=1.0,
            is_high_risk=result.get("is_high_risk", False),
            escalated=result.get("escalated", False),
            escalation_reason=result.get("escalation_reason"),
            sources_json=json.dumps(result.get("sources", [])) if result.get("sources") else None,
        )
        db.add(bot_msg)

        # 4. If a ticket was generated by Sentinel, sync to SQLite
        ticket_id = result.get("ticket_id")
        if ticket_id:
            existing_ticket = db.query(TicketRecord).filter(TicketRecord.id == ticket_id).first()
            if not existing_ticket:
                # Find ticket object in bot.tickets
                bot_ticket: Optional[SupportTicket] = next((t for t in self.bot.tickets if t.id == ticket_id), None)
                if bot_ticket:
                    new_ticket_rec = TicketRecord(
                        id=bot_ticket.id,
                        session_id=active_session_id,
                        customer_id=bot_ticket.customer_id,
                        customer_name=bot_ticket.customer_name,
                        contact_email=getattr(bot_ticket, "customer_email", None),
                        contact_phone=getattr(bot_ticket, "customer_phone", None),
                        order_id=bot_ticket.order_id,
                        product_code=getattr(bot_ticket, "product", ""),
                        issue_description=bot_ticket.issue_description,
                        priority=bot_ticket.priority.value if hasattr(bot_ticket.priority, "value") else str(bot_ticket.priority),
                        priority_score=bot_ticket.priority_score,
                        status="Open",
                        assigned_team=bot_ticket.assigned_team or "general",
                        assigned_agent=bot_ticket.assigned_agent,
                        sla_deadline=bot_ticket.sla_deadline,
                        sla_hours=getattr(bot_ticket, "metadata", {}).get("sla_hours", 4.0),
                        sla_breached=bot_ticket.sla_breached,
                        escalation_reason=result.get("escalation_reason"),
                        handoff_summary=bot_ticket.handoff_summary,
                        duplicate_of=bot_ticket.duplicate_of,
                        created_at=bot_ticket.created_at,
                        updated_at=now,
                    )
                    db.add(new_ticket_rec)

        # 5. Record audit log
        audit = AuditLogRecord(
            event_type="chat_message",
            details=f"Processed message for session={active_session_id}, sentiment={result.get('sentiment')}, high_risk={result.get('is_high_risk')}",
            user_id=customer_id,
            timestamp=now,
        )
        db.add(audit)

        db.commit()

        return {
            "session_id": active_session_id,
            "reply": result.get("reply", ""),
            "sentiment": result.get("sentiment", "neutral"),
            "confidence": result.get("confidence", 1.0),
            "is_high_risk": result.get("is_high_risk", False),
            "risk_category": result.get("risk_category"),
            "risk_level": result.get("risk_level", "none"),
            "escalated": result.get("escalated", False),
            "escalation_reason": result.get("escalation_reason"),
            "ticket_id": result.get("ticket_id"),
            "assigned_team": result.get("assigned_team"),
            "sources": result.get("sources", []),
            "file_result": file_info,
            "timestamp": now,
        }

    def sync_knowledge_to_db(self, db: Session) -> None:
        """Sync in-memory DocumentStore documents to DocumentRecord table."""
        for doc in self.bot.doc_store._documents.values():
            exists = db.query(DocumentRecord).filter(DocumentRecord.id == doc.id).first()
            if not exists:
                rec = DocumentRecord(
                    id=doc.id,
                    title=doc.title,
                    product=doc.product,
                    region=doc.region,
                    access_level=doc.access_level.value if hasattr(doc.access_level, "value") else str(doc.access_level),
                    version=doc.version,
                    effective_date=doc.effective_date,
                    expiry_date=doc.expiry_date,
                    content=doc.content,
                    status="active",
                    accuracy_score=0.95,
                    grounding_score=0.90,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                db.add(rec)
        db.commit()

    def add_document(
        self,
        db: Session,
        title: str,
        content: str,
        product: str = "General",
        region: str = "global",
        access_level: str = "public",
        version: int = 1,
        effective_date: Optional[datetime] = None,
        expiry_date: Optional[datetime] = None,
    ) -> DocumentRecord:
        """Validate with quality tester, add to DocumentStore, and save to database."""
        doc_id = f"kb-{uuid.uuid4().hex[:8]}"
        eff_date = effective_date or datetime.utcnow()

        level_enum = AccessLevel.PUBLIC
        try:
            level_enum = AccessLevel(access_level.lower())
        except Exception:
            level_enum = AccessLevel.PUBLIC

        doc = KnowledgeDocument(
            id=doc_id,
            title=title,
            product=product,
            region=region,
            access_level=level_enum,
            version=version,
            effective_date=eff_date,
            expiry_date=expiry_date,
            content=content,
        )

        # Run quality gate test
        quality_res = self.bot.quality_tester.run_tests(
            new_docs=[doc],
            existing_docs=list(self.bot.doc_store._documents.values()),
        )
        is_approved = quality_res.get("approved", True)
        acc_score = quality_res.get("accuracy_score", 1.0)
        grd_score = quality_res.get("grounding_score", 1.0)
        status = "active" if is_approved else "failed_quality"

        if is_approved:
            self.bot.doc_store.add_document(doc)

        rec = DocumentRecord(
            id=doc_id,
            title=title,
            product=product,
            region=region,
            access_level=access_level,
            version=version,
            effective_date=eff_date,
            expiry_date=expiry_date,
            content=content,
            status=status,
            accuracy_score=acc_score,
            grounding_score=grd_score,
            quarantine_reason="Quality gate thresholds not met" if not is_approved else None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(rec)
        db.commit()
        db.refresh(rec)
        return rec
