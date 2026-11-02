from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, or_
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import AuditLogRecord, DocumentRecord
from backend.schemas import DocumentCreate, DocumentOut
from backend.service import SentinelService

router = APIRouter(prefix="/api/knowledge", tags=["Knowledge Base"])
service = SentinelService.get_instance()


@router.get("/documents", response_model=List[DocumentOut])
def list_documents(
    access_level: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List documents in the knowledge base with filtering and search."""
    service.sync_knowledge_to_db(db)

    query = db.query(DocumentRecord)

    if access_level and access_level != "all":
        query = query.filter(DocumentRecord.access_level.ilike(access_level))

    if status and status != "all":
        query = query.filter(DocumentRecord.status.ilike(status))

    if search:
        term = f"%{search}%"
        query = query.filter(
            or_(
                DocumentRecord.title.ilike(term),
                DocumentRecord.content.ilike(term),
                DocumentRecord.product.ilike(term),
            )
        )

    return query.order_by(desc(DocumentRecord.created_at)).offset(offset).limit(limit).all()


@router.post("/documents", response_model=DocumentOut)
def create_document(req: DocumentCreate, db: Session = Depends(get_db)):
    """
    Submit a new document to the knowledge pipeline.
    Runs automated quality gates (accuracy >= 0.85, grounding >= 0.80).
    Approved documents are indexed in RAG DocumentStore immediately.
    """
    eff_date = None
    if req.effective_date:
        try:
            eff_date = datetime.fromisoformat(req.effective_date.replace("Z", "+00:00"))
        except Exception:
            eff_date = None

    exp_date = None
    if req.expiry_date:
        try:
            exp_date = datetime.fromisoformat(req.expiry_date.replace("Z", "+00:00"))
        except Exception:
            exp_date = None

    # Check for prompt injection in content
    from src.core.utils.helpers import detect_prompt_injection

    has_inj, trigger = detect_prompt_injection(req.content)
    if has_inj:
        # Quarantine invalid/injected document
        doc_rec = DocumentRecord(
            id=f"kb-quar-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            title=req.title,
            product=req.product,
            region=req.region,
            access_level=req.access_level,
            version=req.version,
            effective_date=eff_date or datetime.utcnow(),
            expiry_date=exp_date,
            content=req.content,
            status="quarantined",
            accuracy_score=0.0,
            grounding_score=0.0,
            quarantine_reason=f"Security violation: prompt injection trigger detected ('{trigger}')",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(doc_rec)
        db.commit()
        db.refresh(doc_rec)
        return doc_rec

    doc_rec = service.add_document(
        db=db,
        title=req.title,
        content=req.content,
        product=req.product,
        region=req.region,
        access_level=req.access_level,
        version=req.version,
        effective_date=eff_date,
        expiry_date=exp_date,
    )

    audit = AuditLogRecord(
        event_type="document_created",
        details=f"Document '{req.title}' created (status={doc_rec.status})",
        user_id="admin",
        timestamp=datetime.utcnow(),
    )
    db.add(audit)
    db.commit()

    return doc_rec


@router.post("/sync")
def sync_knowledge(db: Session = Depends(get_db)):
    """Synchronize all active policies into the database."""
    service.sync_knowledge_to_db(db)
    count = db.query(DocumentRecord).count()
    return {"status": "synced", "total_documents": count}

