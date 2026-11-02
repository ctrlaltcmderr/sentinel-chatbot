from datetime import datetime
from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["Health"])


@router.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "Sentinel Chatbot Enterprise API",
        "version": "2.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "subsystems": {
            "sentiment_escalation": "online",
            "ticket_sla": "online",
            "knowledge_pipeline": "online",
            "rag_assistant": "online",
            "multimodal_processor": "online",
            "multilingual_memory": "online",
        },
    }

