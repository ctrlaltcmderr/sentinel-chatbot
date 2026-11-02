from collections import Counter, defaultdict
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import ChatMessage, Conversation, TicketRecord
from backend.schemas import (
    AnalyticsOverview,
    AnalyticsTrends,
    SentimentDistribution,
)
from backend.service import SentinelService

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])
service = SentinelService.get_instance()


@router.get("/overview", response_model=AnalyticsOverview)
def get_overview(db: Session = Depends(get_db)):
    """Compute real operational overview statistics directly from the database."""
    total_convs = db.query(Conversation).count()
    active_convs = db.query(Conversation).filter(Conversation.status == "active").count()
    total_tickets = db.query(TicketRecord).count()
    open_tickets = db.query(TicketRecord).filter(TicketRecord.status.in_(["Open", "In Progress", "Pending"])).count()
    resolved_tickets = db.query(TicketRecord).filter(TicketRecord.status.in_(["Resolved", "Closed"])).count()
    escalated_convs = db.query(Conversation).filter(Conversation.escalated == True).count()
    high_risk_convs = db.query(Conversation).filter(Conversation.is_high_risk == True).count()

    avg_latency = 45.0
    if service.response_latencies:
        avg_latency = sum(service.response_latencies) / len(service.response_latencies)

    return AnalyticsOverview(
        total_conversations=total_convs,
        active_conversations=active_convs,
        total_tickets=total_tickets,
        open_tickets=open_tickets,
        resolved_tickets=resolved_tickets,
        escalated_conversations=escalated_convs,
        high_risk_incidents=high_risk_convs,
        average_response_time_ms=round(avg_latency, 2),
    )


@router.get("/sentiment", response_model=SentimentDistribution)
def get_sentiment_analytics(db: Session = Depends(get_db)):
    """Aggregate customer sentiment distribution and confidence scores."""
    messages = db.query(ChatMessage).filter(ChatMessage.sender == "customer").all()

    distribution = {
        "positive": 0,
        "neutral": 0,
        "negative": 0,
        "frustrated": 0,
        "urgent": 0,
        "sarcastic": 0,
    }
    confidences = []
    high_risk_count = 0

    for m in messages:
        if m.sentiment and m.sentiment.lower() in distribution:
            distribution[m.sentiment.lower()] += 1
        elif m.sentiment:
            distribution["neutral"] += 1

        if m.confidence is not None:
            confidences.append(m.confidence)

        if m.is_high_risk:
            high_risk_count += 1

    avg_conf = (sum(confidences) / len(confidences)) if confidences else 0.85

    return SentimentDistribution(
        distribution=distribution,
        avg_confidence=round(avg_conf, 3),
        high_risk_count=high_risk_count,
    )


@router.get("/trends", response_model=AnalyticsTrends)
def get_trends(db: Session = Depends(get_db)):
    """Compute 7-day timeline trends, team workload, and ticket priorities."""
    now = datetime.utcnow()
    seven_days_ago = now - timedelta(days=6)

    # 1. Activity timeline
    timeline_map = defaultdict(lambda: {"conversations": 0, "escalations": 0})
    for i in range(7):
        day_str = (seven_days_ago + timedelta(days=i)).strftime("%Y-%m-%d")
        timeline_map[day_str] = {"conversations": 0, "escalations": 0}

    convs = db.query(Conversation).all()
    for c in convs:
        d_str = c.created_at.strftime("%Y-%m-%d")
        if d_str in timeline_map:
            timeline_map[d_str]["conversations"] += 1
            if c.escalated:
                timeline_map[d_str]["escalations"] += 1

    activity_timeline = [
        {"date": date, "conversations": counts["conversations"], "escalations": counts["escalations"]}
        for date, counts in sorted(timeline_map.items())
    ]

    # 2. Sentiment counts
    sentiment_counts = {
        "positive": 0,
        "neutral": 0,
        "negative": 0,
        "frustrated": 0,
        "urgent": 0,
        "sarcastic": 0,
    }
    for c in convs:
        s = (c.last_sentiment or "neutral").lower()
        if s in sentiment_counts:
            sentiment_counts[s] += 1

    # 3. Priority counts
    tickets = db.query(TicketRecord).all()
    priority_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for t in tickets:
        p = (t.priority or "medium").lower()
        if p in priority_counts:
            priority_counts[p] += 1

    # 4. Team workload
    team_workload = defaultdict(int)
    for t in tickets:
        if t.status in ["Open", "In Progress", "Pending", "Escalated"]:
            team_workload[t.assigned_team or "general"] += 1

    # 5. Language distribution
    languages = {"en": 0, "es": 0, "fr": 0, "hi": 0}
    for c in convs:
        lang = c.language or "en"
        if lang in languages:
            languages[lang] += 1
        else:
            languages["en"] += 1

    # 6. Status distribution
    status_distribution = defaultdict(int)
    for t in tickets:
        status_distribution[t.status] += 1

    return AnalyticsTrends(
        activity_timeline=activity_timeline,
        sentiment_counts=sentiment_counts,
        priority_counts=priority_counts,
        team_workload=dict(team_workload),
        language_distribution=languages,
        status_distribution=dict(status_distribution),
    )

