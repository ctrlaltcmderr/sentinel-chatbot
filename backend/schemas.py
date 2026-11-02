from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ──────────────────────── Chat Schemas ────────────────────────

class MessageRequest(BaseModel):
    customer_id: str = Field(default="cust-101", description="Unique customer ID")
    session_id: Optional[str] = Field(default=None, description="Active session ID or None for auto")
    message: str = Field(..., min_length=1, description="Raw message from customer")
    reference_date: Optional[str] = Field(default=None, description="Optional ISO reference date for historical queries")
    user_access_level: str = Field(default="public", description="public, internal, restricted, confidential")
    uploaded_file: Optional[str] = Field(default=None, description="Path to already validated uploaded file")


class ChatMessageOut(BaseModel):
    id: int
    session_id: str
    sender: str
    content: str
    timestamp: datetime
    language: str = "en"
    sentiment: Optional[str] = None
    confidence: Optional[float] = None
    is_high_risk: bool = False
    escalated: bool = False
    escalation_reason: Optional[str] = None
    sources: List[Any] = []
    file_info: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    session_id: str
    reply: str
    sentiment: str
    confidence: float
    is_high_risk: bool
    escalated: bool
    escalation_reason: Optional[str] = None
    ticket_id: Optional[str] = None
    assigned_team: Optional[str] = None
    sources: List[Any] = []
    file_result: Optional[Dict[str, Any]] = None
    timestamp: datetime


class ConversationOut(BaseModel):
    id: str
    customer_id: str
    customer_name: Optional[str] = None
    title: str
    status: str
    last_sentiment: str
    last_confidence: float
    is_high_risk: bool
    escalated: bool
    escalation_reason: Optional[str] = None
    language: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0
    messages: Optional[List[ChatMessageOut]] = None

    class Config:
        from_attributes = True


# ──────────────────────── Ticket Schemas ────────────────────────

class InternalNoteOut(BaseModel):
    id: int
    ticket_id: str
    author: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class InternalNoteCreate(BaseModel):
    author: str = Field(default="Support Agent")
    content: str = Field(..., min_length=1)


class TicketOut(BaseModel):
    id: str
    session_id: Optional[str] = None
    customer_id: str
    customer_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    order_id: Optional[str] = None
    product_code: Optional[str] = None
    issue_description: str
    priority: str
    priority_score: float
    status: str
    assigned_team: str
    assigned_agent: Optional[str] = None
    sla_deadline: Optional[datetime] = None
    sla_hours: Optional[float] = None
    sla_breached: bool = False
    escalation_reason: Optional[str] = None
    handoff_summary: Optional[str] = None
    duplicate_of: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    notes: List[InternalNoteOut] = []

    class Config:
        from_attributes = True


class TicketUpdate(BaseModel):
    status: Optional[str] = None
    assigned_team: Optional[str] = None
    assigned_agent: Optional[str] = None
    priority: Optional[str] = None


# ──────────────────────── Knowledge Schemas ────────────────────────

class DocumentCreate(BaseModel):
    title: str = Field(..., min_length=3)
    content: str = Field(..., min_length=10)
    product: str = Field(default="General")
    region: str = Field(default="global")
    access_level: str = Field(default="public")
    version: int = Field(default=1)
    effective_date: Optional[str] = None
    expiry_date: Optional[str] = None


class DocumentOut(BaseModel):
    id: str
    title: str
    product: str
    region: str
    access_level: str
    version: int
    effective_date: datetime
    expiry_date: Optional[datetime] = None
    content: str
    status: str
    accuracy_score: Optional[float] = None
    grounding_score: Optional[float] = None
    quarantine_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ──────────────────────── Analytics Schemas ────────────────────────

class AnalyticsOverview(BaseModel):
    total_conversations: int
    active_conversations: int
    total_tickets: int
    open_tickets: int
    resolved_tickets: int
    escalated_conversations: int
    high_risk_incidents: int
    average_response_time_ms: float


class SentimentDistribution(BaseModel):
    distribution: Dict[str, int]
    avg_confidence: float
    high_risk_count: int


class AnalyticsTrends(BaseModel):
    activity_timeline: List[Dict[str, Any]]
    sentiment_counts: Dict[str, int]
    priority_counts: Dict[str, int]
    team_workload: Dict[str, int]
    language_distribution: Dict[str, int]
    status_distribution: Dict[str, int]


# ──────────────────────── Admin Schemas ────────────────────────

class AdminSettingsOut(BaseModel):
    app_name: str
    version: str
    business_hours_start: int
    business_hours_end: int
    sla_hours: Dict[str, float]
    escalation_negative_count: int
    unresolved_escalation_minutes: int
    session_timeout_minutes: int
    supported_languages: List[str]
    access_levels: List[str]
    maintenance_window_start: int
    maintenance_window_end: int


class AdminSettingsUpdate(BaseModel):
    business_hours_start: Optional[int] = None
    business_hours_end: Optional[int] = None
    sla_hours: Optional[Dict[str, float]] = None
    escalation_negative_count: Optional[int] = None
    unresolved_escalation_minutes: Optional[int] = None
    session_timeout_minutes: Optional[int] = None

