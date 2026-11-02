"""
Core data models shared across all Sentinel Chatbot components.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


# ──────────────────────────── Enumerations ────────────────────────────

class SentimentType(Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    FRUSTRATED = "frustrated"
    URGENT = "urgent"
    SARCASTIC = "sarcastic"


class Priority(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TicketStatus(Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    WAITING_CUSTOMER = "waiting_customer"
    ESCALATED = "escalated"
    RESOLVED = "resolved"
    CLOSED = "closed"


class EscalationReason(Enum):
    REPEATED_NEGATIVE = "repeated_negative_sentiment"
    HIGH_RISK_ISSUE = "high_risk_issue"
    AFTER_HOURS_URGENT = "after_hours_urgent"
    UNRESOLVED_TIMEOUT = "unresolved_timeout"
    SLA_BREACH = "sla_breach"
    CUSTOMER_REQUEST = "customer_requested_escalation"
    SYSTEM_TRIGGER = "system_triggered"


class AccessLevel(Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    RESTRICTED = "restricted"
    CONFIDENTIAL = "confidential"


class DocumentStatus(Enum):
    ACTIVE = "active"
    DRAFT = "draft"
    EXPIRED = "expired"
    FUTURE = "future"
    QUARANTINED = "quarantined"
    ARCHIVED = "archived"


class FileProcessingStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    QUEUED_BACKGROUND = "queued_background"
    REJECTED = "rejected"


# ──────────────────────────── Data Models ────────────────────────────

@dataclass
class Message:
    """A single chat message."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = ""
    customer_id: str = ""
    content: str = ""
    language: str = "en"
    detected_language: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    is_customer: bool = True
    attachments: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SentimentResult:
    """Result of sentiment analysis."""
    sentiment: SentimentType = SentimentType.NEUTRAL
    confidence: float = 0.0
    scores: Dict[str, float] = field(default_factory=dict)
    language: str = "en"
    is_high_risk: bool = False
    high_risk_triggers: List[str] = field(default_factory=list)
    risk_category: Optional[str] = None
    risk_level: str = "none"  # "critical", "high", "medium", "none"
    is_sarcastic: bool = False
    recommended_tone: str = "professional"
    raw_text: str = ""
    analysis_notes: str = ""


@dataclass
class ConversationContext:
    """Conversation context tracking."""
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    customer_id: str = ""
    messages: List[Message] = field(default_factory=list)
    sentiment_history: List[SentimentResult] = field(default_factory=list)
    current_language: str = "en"
    detected_languages: List[str] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    is_resolved: bool = False
    is_escalated: bool = False
    escalation_records: List[Dict[str, Any]] = field(default_factory=list)
    summary: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_message(self, message: Message) -> None:
        self.messages.append(message)
        self.last_activity = message.timestamp

    @property
    def duration_minutes(self) -> float:
        if not self.messages:
            return 0.0
        return (self.last_activity - self.started_at).total_seconds() / 60


@dataclass
class EscalationRecord:
    """Record of an escalation event."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = ""
    reason: EscalationReason = EscalationReason.SYSTEM_TRIGGER
    activated_condition: str = ""
    conversation_summary: str = ""
    sentiment_at_escalation: Optional[SentimentResult] = None
    priority: Priority = Priority.HIGH
    timestamp: datetime = field(default_factory=datetime.utcnow)
    queue_type: str = "standard"  # "standard", "on_call", "next_business_day"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SupportTicket:
    """Structured support ticket."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = ""
    customer_name: str = ""
    customer_email: str = ""
    customer_phone: str = ""
    customer_id: str = ""
    order_id: str = ""
    product: str = ""
    issue_category: str = ""
    issue_description: str = ""
    evidence: List[str] = field(default_factory=list)
    priority: Priority = Priority.MEDIUM
    priority_score: float = 0.0
    status: TicketStatus = TicketStatus.OPEN
    assigned_team: str = ""
    assigned_agent: str = ""
    sla_deadline: Optional[datetime] = None
    sla_warning_sent: bool = False
    sla_breached: bool = False
    related_tickets: List[str] = field(default_factory=list)
    duplicate_of: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    handoff_summary: str = ""
    missing_fields: List[str] = field(default_factory=list)
    conversation_summary: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class KnowledgeDocument:
    """A document in the knowledge base."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    content: str = ""
    content_hash: str = ""
    version: int = 1
    product: str = ""
    region: str = ""
    access_level: AccessLevel = AccessLevel.PUBLIC
    effective_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    status: DocumentStatus = DocumentStatus.ACTIVE
    source_file: str = ""
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RAGResult:
    """Result from RAG knowledge retrieval."""
    answer: str = ""
    confidence: float = 0.0
    sources: List[Dict[str, Any]] = field(default_factory=list)
    is_ambiguous: bool = False
    requires_clarification: bool = False
    clarification_message: str = ""
    unsupported_claims: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FileProcessingResult:
    """Result of processing an uploaded file."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    original_filename: str = ""
    file_type: str = ""
    status: FileProcessingStatus = FileProcessingStatus.PENDING
    extracted_data: Dict[str, Any] = field(default_factory=dict)
    extracted_text: str = ""
    order_ids: List[str] = field(default_factory=list)
    dates: List[str] = field(default_factory=list)
    amounts: List[str] = field(default_factory=list)
    product_info: List[str] = field(default_factory=list)
    error_codes: List[str] = field(default_factory=list)
    conflicts: List[str] = field(default_factory=list)
    quality_score: float = 1.0
    is_safe: bool = True
    safety_issues: List[str] = field(default_factory=list)
    processing_time_seconds: float = 0.0
    queued_for_background: bool = False
    retention_expiry: Optional[datetime] = None
    masked_log_entry: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SessionState:
    """Customer session state."""
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    customer_id: str = ""
    current_language: str = "en"
    messages: List[Message] = field(default_factory=list)
    context_summary: str = ""
    started_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    is_active: bool = True
    expired: bool = False
    previous_session_summary: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def inactivity_minutes(self) -> float:
        return (datetime.utcnow() - self.last_activity).total_seconds() / 60


@dataclass
class MonitoringMetrics:
    """System monitoring metrics."""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    latency_ms: float = 0.0
    confidence_score: float = 0.0
    escalation_count: int = 0
    failure_count: int = 0
    active_sessions: int = 0
    active_tickets: int = 0
    sla_breaches: int = 0
    component: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

