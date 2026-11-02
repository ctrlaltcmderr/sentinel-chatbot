import os
import shutil
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import desc, or_
from sqlalchemy.orm import Session

from backend.config import UPLOAD_DIR
from backend.database import get_db
from backend.models import ChatMessage, Conversation
from backend.schemas import (
    ChatMessageOut,
    ConversationOut,
    MessageRequest,
    MessageResponse,
)
from backend.service import SentinelService

router = APIRouter(prefix="/api/chat", tags=["Chat"])
service = SentinelService.get_instance()


@router.post("/message", response_model=MessageResponse)
def send_message(req: MessageRequest, db: Session = Depends(get_db)):
    """
    Handle customer message via the SentinelChatbot engine,
    persist in database, and return comprehensive response.
    """
    try:
        res = service.process_message(
            db=db,
            customer_id=req.customer_id,
            message_text=req.message,
            session_id=req.session_id,
            reference_date=req.reference_date,
            user_access_level=req.user_access_level,
            uploaded_file=req.uploaded_file,
        )
        return MessageResponse(**res)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Message processing failed: {str(e)}")


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    customer_id: str = Query("cust-101"),
    session_id: Optional[str] = Query(None),
):
    """
    Upload and validate a file (image, PDF, invoice, receipt, text),
    execute OCR and structured extraction via MultimodalProcessor.
    """
    # 1. Validate file extension
    ext = os.path.splitext(file.filename)[1].lower().lstrip(".")
    allowed = ["txt", "pdf", "png", "jpg", "jpeg", "csv", "json"]
    if ext not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{ext}'. Allowed: {', '.join(allowed)}",
        )

    # 2. Save securely to UPLOAD_DIR
    safe_name = f"{uuid.uuid4().hex}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, safe_name)

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File save error: {str(e)}")

    # 3. Check file size limit (10MB)
    size_mb = os.path.getsize(file_path) / (1024 * 1024)
    if size_mb > 10.0:
        os.remove(file_path)
        raise HTTPException(status_code=400, detail="File size exceeds maximum 10MB limit.")

    # 4. Process file with existing MultimodalProcessor
    try:
        result = service.bot.multimodal_processor.process_file(file_path)
        if not result.is_safe:
            return {
                "success": False,
                "file_path": file_path,
                "filename": file.filename,
                "is_safe": False,
                "status": "rejected",
                "message": "File violates safety or prompt-injection policy.",
            }

        return {
            "success": True,
            "file_path": file_path,
            "filename": file.filename,
            "file_type": result.file_type,
            "is_safe": result.is_safe,
            "status": result.status.value if hasattr(result.status, "value") else str(result.status),
            "quality_score": result.quality_score,
            "extracted_text": result.extracted_text[:300] if result.extracted_text else "",
            "extracted_order_ids": result.order_ids,
            "extracted_dates": result.dates,
            "extracted_amounts": result.amounts,
            "extracted_error_codes": result.error_codes,
            "conflicts_detected": result.conflicts,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Multimodal processing error: {str(e)}")


@router.get("/conversations", response_model=List[ConversationOut])
def list_conversations(
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List all active or past customer support conversations."""
    query = db.query(Conversation)

    if status and status != "all":
        query = query.filter(Conversation.status == status)

    if search:
        term = f"%{search}%"
        query = query.filter(
            or_(
                Conversation.title.ilike(term),
                Conversation.customer_id.ilike(term),
                Conversation.customer_name.ilike(term),
                Conversation.id.ilike(term),
            )
        )

    conversations = query.order_by(desc(Conversation.updated_at)).offset(offset).limit(limit).all()

    out = []
    for c in conversations:
        m_count = db.query(ChatMessage).filter(ChatMessage.session_id == c.id).count()
        item = ConversationOut.model_validate(c)
        item.message_count = m_count
        out.append(item)
    return out


@router.get("/conversations/{session_id}", response_model=ConversationOut)
def get_conversation(session_id: str, db: Session = Depends(get_db)):
    """Retrieve full conversation details along with its ordered chat history."""
    conv = db.query(Conversation).filter(Conversation.id == session_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.timestamp.asc())
        .all()
    )

    out = ConversationOut.model_validate(conv)
    out.messages = [ChatMessageOut.model_validate(m) for m in messages]
    out.message_count = len(messages)
    return out


@router.delete("/conversations/{session_id}")
def delete_conversation(session_id: str, db: Session = Depends(get_db)):
    """Delete a conversation and its messages."""
    conv = db.query(Conversation).filter(Conversation.id == session_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    db.delete(conv)
    db.commit()
    return {"status": "deleted", "session_id": session_id}
