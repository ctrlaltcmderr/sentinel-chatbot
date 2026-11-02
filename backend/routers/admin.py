from fastapi import APIRouter, HTTPException
from backend.schemas import AdminSettingsOut, AdminSettingsUpdate
from backend.service import SentinelService

router = APIRouter(prefix="/api/admin", tags=["Admin Settings"])
service = SentinelService.get_instance()


@router.get("/settings", response_model=AdminSettingsOut)
def get_settings():
    """Retrieve operational system configuration settings."""
    cfg = service.bot.settings
    return AdminSettingsOut(
        app_name="Sentinel Chatbot",
        version="2.0.0",
        business_hours_start=cfg.business_hours.start_hour,
        business_hours_end=cfg.business_hours.end_hour,
        sla_hours={
            "critical": cfg.sla.critical_response_hours,
            "high": cfg.sla.high_response_hours,
            "medium": cfg.sla.medium_response_hours,
            "low": cfg.sla.low_response_hours,
        },
        escalation_negative_count=cfg.sentiment.escalation_negative_count,
        unresolved_escalation_minutes=cfg.sentiment.unresolved_escalation_minutes,
        session_timeout_minutes=cfg.session.inactivity_timeout_minutes,
        supported_languages=cfg.language.supported_languages,
        access_levels=["public", "internal", "restricted", "confidential"],
        maintenance_window_start=cfg.knowledge_base.maintenance_window_start_hour,
        maintenance_window_end=cfg.knowledge_base.maintenance_window_end_hour,
    )


@router.patch("/settings", response_model=AdminSettingsOut)
def update_settings(update: AdminSettingsUpdate):
    """Dynamically update backend parameters."""
    cfg = service.bot.settings

    if update.business_hours_start is not None:
        cfg.business_hours.start_hour = update.business_hours_start
    if update.business_hours_end is not None:
        cfg.business_hours.end_hour = update.business_hours_end

    if update.sla_hours:
        if "critical" in update.sla_hours:
            cfg.sla.critical_response_hours = update.sla_hours["critical"]
        if "high" in update.sla_hours:
            cfg.sla.high_response_hours = update.sla_hours["high"]
        if "medium" in update.sla_hours:
            cfg.sla.medium_response_hours = update.sla_hours["medium"]
        if "low" in update.sla_hours:
            cfg.sla.low_response_hours = update.sla_hours["low"]

    if update.escalation_negative_count is not None:
        cfg.sentiment.escalation_negative_count = update.escalation_negative_count
    if update.unresolved_escalation_minutes is not None:
        cfg.sentiment.unresolved_escalation_minutes = update.unresolved_escalation_minutes
    if update.session_timeout_minutes is not None:
        cfg.session.inactivity_timeout_minutes = update.session_timeout_minutes

    return get_settings()
