from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, or_
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import AuditLogRecord, InternalNoteRecord, TicketRecord
from backend.schemas import (
    InternalNoteCreate,
    InternalNoteOut,
    TicketOut,
    TicketUpdate,
)
from backend.service import SentinelService
from src.core.utils.helpers import TimeProvider

router = APIRouter(prefix="/api/tickets", tags=["Tickets"])
service = SentinelService.get_instance()


@router.get("", response_model=List[TicketOut])
def list_tickets(
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    team: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List support tickets with multiple filter options."""
    query = db.query(TicketRecord)

    if status and status != "all":
        query = query.filter(TicketRecord.status.ilike(status))

    if priority and priority != "all":
        query = query.filter(TicketRecord.priority.ilike(priority))

    if team and team != "all":
        query = query.filter(TicketRecord.assigned_team.ilike(team))

    if search:
        term = f"%{search}%"
        query = query.filter(
            or_(
                TicketRecord.id.ilike(term),
                TicketRecord.customer_id.ilike(term),
                TicketRecord.customer_name.ilike(term),
                TicketRecord.order_id.ilike(term),
                TicketRecord.issue_description.ilike(term),
            )
        )

    tickets = query.order_by(desc(TicketRecord.created_at)).offset(offset).limit(limit).all()

    # Check SLA breach dynamically
    now = TimeProvider.now()
    for t in tickets:
        if t.sla_deadline and t.status not in ["Resolved", "Closed"] and now > t.sla_deadline:
            t.sla_breached = True

    return tickets


@router.get("/{ticket_id}", response_model=TicketOut)
def get_ticket(ticket_id: str, db: Session = Depends(get_db)):
    """Retrieve comprehensive details of a single ticket including internal notes."""
    ticket = db.query(TicketRecord).filter(TicketRecord.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    # Update SLA status if breached
    now = TimeProvider.now()
    if ticket.sla_deadline and ticket.status not in ["Resolved", "Closed"] and now > ticket.sla_deadline:
        ticket.sla_breached = True
        db.commit()

    return ticket


@router.patch("/{ticket_id}", response_model=TicketOut)
def update_ticket(ticket_id: str, req: TicketUpdate, db: Session = Depends(get_db)):
    """Update ticket status, priority, or team assignment."""
    ticket = db.query(TicketRecord).filter(TicketRecord.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    if req.status is not None:
        valid_statuses = ["Open", "In Progress", "Pending", "Escalated", "Resolved", "Closed"]
        matching = next((s for s in valid_statuses if s.lower() == req.status.lower()), None)
        if matching:
            ticket.status = matching
        else:
            ticket.status = req.status

    if req.assigned_team is not None:
        ticket.assigned_team = req.assigned_team

    if req.assigned_agent is not None:
        ticket.assigned_agent = req.assigned_agent

    if req.priority is not None:
        ticket.priority = req.priority.lower()

    ticket.updated_at = datetime.utcnow()

    # Audit log
    audit = AuditLogRecord(
        event_type="ticket_updated",
        details=f"Ticket {ticket_id} updated: status={ticket.status}, team={ticket.assigned_team}",
        user_id="agent",
        timestamp=datetime.utcnow(),
    )
    db.add(audit)
    db.commit()
    db.refresh(ticket)
    return ticket


@router.post("/{ticket_id}/notes", response_model=InternalNoteOut)
def add_internal_note(ticket_id: str, req: InternalNoteCreate, db: Session = Depends(get_db)):
    """Add an internal note to a ticket for human agent collaboration."""
    ticket = db.query(TicketRecord).filter(TicketRecord.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    note = InternalNoteRecord(
        ticket_id=ticket_id,
        author=req.author,
        content=req.content,
        created_at=datetime.utcnow(),
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return note

