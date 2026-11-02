import json
from datetime import datetime
from typing import Any, List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from backend.database import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String(64), primary_key=True, index=True)  # session_id
    customer_id = Column(String(64), nullable=False, index=True)
    customer_name = Column(String(128), nullable=True)
    title = Column(String(256), nullable=False, default="New Conversation")
    status = Column(String(32), nullable=False, default="active")  # active, escalated, resolved, closed
    last_sentiment = Column(String(32), nullable=False, default="neutral")
    last_confidence = Column(Float, nullable=False, default=1.0)
    is_high_risk = Column(Boolean, nullable=False, default=False)
    escalated = Column(Boolean, nullable=False, default=False)
    escalation_reason = Column(String(128), nullable=True)
    language = Column(String(16), nullable=False, default="en")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    messages = relationship(
        "ChatMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="ChatMessage.timestamp.asc()",
    )
    tickets = relationship("TicketRecord", back_populates="conversation")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    sender = Column(String(32), nullable=False)  # "customer" or "sentinel"
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    language = Column(String(16), nullable=False, default="en")
    sentiment = Column(String(32), nullable=True)
    confidence = Column(Float, nullable=True)
    is_high_risk = Column(Boolean, default=False, nullable=False)
    escalated = Column(Boolean, default=False, nullable=False)
    escalation_reason = Column(String(128), nullable=True)
    sources_json = Column(Text, nullable=True)  # JSON serialized list of source citations
    file_info_json = Column(Text, nullable=True)  # JSON serialized file processing details

    conversation = relationship("Conversation", back_populates="messages")

    @property
    def sources(self) -> List[Any]:
        if not self.sources_json:
            return []
        try:
            return json.loads(self.sources_json)
        except Exception:
            return []

    @sources.setter
    def sources(self, value: List[Any]) -> None:
        self.sources_json = json.dumps(value) if value else None

    @property
    def file_info(self) -> Optional[dict]:
        if not self.file_info_json:
            return None
        try:
            return json.loads(self.file_info_json)
        except Exception:
            return None

    @file_info.setter
    def file_info(self, value: Optional[dict]) -> None:
        self.file_info_json = json.dumps(value) if value else None


class TicketRecord(Base):
    __tablename__ = "tickets"

    id = Column(String(64), primary_key=True, index=True)
    session_id = Column(String(64), ForeignKey("conversations.id"), nullable=True, index=True)
    customer_id = Column(String(64), nullable=False, index=True)
    customer_name = Column(String(128), nullable=True)
    contact_email = Column(String(128), nullable=True)
    contact_phone = Column(String(64), nullable=True)
    order_id = Column(String(64), nullable=True, index=True)
    product_code = Column(String(64), nullable=True)
    issue_description = Column(Text, nullable=False)
    priority = Column(String(32), nullable=False, default="medium")  # low, medium, high, critical
    priority_score = Column(Float, nullable=False, default=0.5)
    status = Column(String(32), nullable=False, default="Open")  # Open, In Progress, Pending, Escalated, Resolved, Closed
    assigned_team = Column(String(64), nullable=False, default="general")
    assigned_agent = Column(String(64), nullable=True)
    sla_deadline = Column(DateTime, nullable=True)
    sla_hours = Column(Float, nullable=True)
    sla_breached = Column(Boolean, default=False, nullable=False)
    escalation_reason = Column(String(128), nullable=True)
    handoff_summary = Column(Text, nullable=True)
    duplicate_of = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    conversation = relationship("Conversation", back_populates="tickets")
    notes = relationship(
        "InternalNoteRecord",
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="InternalNoteRecord.created_at.desc()",
    )


class InternalNoteRecord(Base):
    __tablename__ = "ticket_notes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticket_id = Column(String(64), ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    author = Column(String(128), nullable=False, default="Support Agent")
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    ticket = relationship("TicketRecord", back_populates="notes")


class DocumentRecord(Base):
    __tablename__ = "knowledge_documents"

    id = Column(String(64), primary_key=True, index=True)
    title = Column(String(256), nullable=False)
    product = Column(String(128), nullable=False, default="General")
    region = Column(String(64), nullable=False, default="global")
    access_level = Column(String(32), nullable=False, default="public")  # public, internal, restricted, confidential
    version = Column(Integer, nullable=False, default=1)
    effective_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    expiry_date = Column(DateTime, nullable=True)
    content = Column(Text, nullable=False)
    file_path = Column(String(512), nullable=True)
    status = Column(String(32), nullable=False, default="active")  # active, quarantined, failed_quality, archived
    accuracy_score = Column(Float, nullable=True)
    grounding_score = Column(Float, nullable=True)
    quarantine_reason = Column(String(256), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class AuditLogRecord(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_type = Column(String(64), nullable=False, index=True)
    details = Column(Text, nullable=False)
    user_id = Column(String(64), nullable=False, default="system")
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

