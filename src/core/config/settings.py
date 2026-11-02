"""
Sentinel Chatbot - Central Configuration Management.

All system settings, thresholds, business hours, SLA rules,
language configs, and feature flags are managed here.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import time, datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from pathlib import Path


class Environment(Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class BusinessHoursConfig:
    """Business hours configuration."""
    start_hour: int = 9
    start_minute: int = 0
    end_hour: int = 18
    end_minute: int = 0
    timezone: str = "Asia/Kolkata"
    weekends: List[int] = field(default_factory=lambda: [5, 6])  # Saturday=5, Sunday=6
    holidays: List[str] = field(default_factory=list)  # ISO date strings

    def is_business_hours(self, dt: Optional[datetime] = None) -> bool:
        """Check if given datetime falls within business hours."""
        try:
            from zoneinfo import ZoneInfo
            tz = ZoneInfo(self.timezone)
        except Exception:
            try:
                import pytz
                tz = pytz.timezone(self.timezone)
            except Exception:
                tz = None

        if dt is None:
            dt = datetime.now(tz) if tz else datetime.now()
        elif dt.tzinfo is not None and tz is not None:
            dt = dt.astimezone(tz)

        if dt.weekday() in self.weekends:
            return False
        date_str = dt.strftime("%Y-%m-%d")
        if date_str in self.holidays:
            return False
        current_time = dt.time()
        start = time(self.start_hour, self.start_minute)
        end = time(self.end_hour, self.end_minute)
        return start <= current_time <= end

    def next_business_day(self, dt: Optional[datetime] = None) -> datetime:
        """Get next business day start time."""
        from datetime import timedelta
        try:
            from zoneinfo import ZoneInfo
            tz = ZoneInfo(self.timezone)
        except Exception:
            try:
                import pytz
                tz = pytz.timezone(self.timezone)
            except Exception:
                tz = None

        if dt is None:
            dt = datetime.now(tz) if tz else datetime.now()
        elif dt.tzinfo is not None and tz is not None:
            dt = dt.astimezone(tz)

        next_day = dt + timedelta(days=1)
        next_day = next_day.replace(
            hour=self.start_hour, minute=self.start_minute, second=0, microsecond=0
        )
        while (next_day.weekday() in self.weekends or
               next_day.strftime("%Y-%m-%d") in self.holidays):
            next_day += timedelta(days=1)
        return next_day


@dataclass
class SLAConfig:
    """SLA rules configuration."""
    critical_response_hours: float = 1.0
    high_response_hours: float = 4.0
    medium_response_hours: float = 8.0
    low_response_hours: float = 24.0
    warning_threshold_percent: float = 75.0
    exclude_weekends: bool = True
    exclude_holidays: bool = True
    auto_escalate_on_breach: bool = True


@dataclass
class SentimentConfig:
    """Sentiment analysis configuration."""
    confidence_threshold: float = 0.6
    escalation_negative_count: int = 3
    unresolved_escalation_minutes: int = 15
    high_risk_keywords: List[str] = field(default_factory=lambda: [
        "account compromise", "hacked", "unauthorized access", "accessed my account",
        "without permission", "unauthorized payment", "unauthorized charge",
        "unauthorized transaction", "duplicate payment", "double charged",
        "charged twice", "legal action", "lawyer", "lawsuit", "sue", "court",
        "attorney", "fraud", "stolen", "identity theft", "account takeover"
    ])
    sarcasm_indicators: List[str] = field(default_factory=lambda: [
        "oh great", "wonderful", "fantastic", "brilliant",
        "thanks a lot", "how lovely", "what a surprise",
        "oh really", "yeah right", "sure thing"
    ])


@dataclass
class LanguageConfig:
    """Multilingual support configuration."""
    supported_languages: List[str] = field(default_factory=lambda: [
        "en", "es", "fr", "hi"  # English, Spanish, French, Hindi
    ])
    default_language: str = "en"
    confidence_threshold: float = 0.7
    context_window_size: int = 10
    session_timeout_minutes: int = 30
    session_restore_hours: int = 24


@dataclass
class SessionConfig:
    """Session management configuration."""
    inactivity_timeout_minutes: int = 30
    restore_window_hours: int = 24
    max_context_messages: int = 10


@dataclass
class KnowledgeBaseConfig:
    """Knowledge base pipeline configuration."""
    update_schedule_hour: int = 2  # 2 AM
    update_schedule_minute: int = 0
    maintenance_window_start_hour: int = 1
    maintenance_window_end_hour: int = 5
    retry_intervals_minutes: List[int] = field(default_factory=lambda: [15, 30, 60])
    health_check_window_minutes: int = 5
    min_accuracy_threshold: float = 0.85
    min_grounding_threshold: float = 0.80
    data_directory: str = "data/knowledge_base"
    quarantine_directory: str = "data/quarantine"
    versions_directory: str = "data/versions"


@dataclass
class MultimodalConfig:
    """Multimodal processing configuration."""
    processing_timeout_seconds: int = 30
    file_retention_hours: int = 72
    max_file_size_mb: int = 25
    supported_image_formats: List[str] = field(
        default_factory=lambda: ["png", "jpg", "jpeg", "gif", "bmp", "tiff"]
    )
    supported_document_formats: List[str] = field(
        default_factory=lambda: ["pdf", "txt", "csv", "json"]
    )
    min_image_quality_score: float = 0.4
    upload_directory: str = "data/uploads"


@dataclass
class TicketConfig:
    """Ticket management configuration."""
    mandatory_fields: List[str] = field(default_factory=lambda: [
        "customer_name", "issue_description", "contact_email"
    ])
    severity_weights: Dict[str, float] = field(default_factory=lambda: {
        "sentiment": 0.25,
        "severity": 0.30,
        "waiting_time": 0.15,
        "customer_impact": 0.20,
        "sla_urgency": 0.10
    })
    teams: Dict[str, List[str]] = field(default_factory=lambda: {
        "billing": ["billing_agent_1", "billing_agent_2"],
        "technical": ["tech_agent_1", "tech_agent_2"],
        "account_security": ["security_agent_1"],
        "general": ["general_agent_1", "general_agent_2"],
        "shipping": ["shipping_agent_1"],
    })
    agent_max_workload: int = 10


@dataclass
class SecurityConfig:
    """Security configuration."""
    access_levels: List[str] = field(default_factory=lambda: [
        "public", "internal", "restricted", "confidential"
    ])
    sensitive_patterns: List[str] = field(default_factory=lambda: [
        r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",  # Credit card
        r"\b\d{3}-\d{2}-\d{4}\b",  # SSN
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # Email
        r"(?:\+\d{1,3}[-\s]?)?\(?\d{3}\)?[-\s]?\d{3}[-\s]?\d{4}",  # Formatted phone
        r"\b\d{10,12}\b",  # Raw phone numbers
    ])
    prompt_injection_patterns: List[str] = field(default_factory=lambda: [
        r"ignore\s+(?:all\s+|previous\s+|above\s+)*(?:instructions|rules|prompts)",
        r"you\s+are\s+now\s+(a|an|the)",
        r"disregard\s+(your|all|the)\s+(rules|instructions|guidelines)",
        r"forget\s+(everything|your\s+instructions|all\s+rules)",
        r"system\s*:\s*",
        r"<\s*system\s*>",
        r"ADMIN\s*OVERRIDE",
        r"bypass\s+(security|filter|restriction)",
    ])
    max_login_attempts: int = 5
    token_expiry_hours: int = 8


@dataclass
class MonitoringConfig:
    """Monitoring and alerting configuration."""
    latency_warning_ms: int = 2000
    latency_critical_ms: int = 5000
    min_confidence_threshold: float = 0.5
    alert_on_escalation: bool = True
    log_level: str = "INFO"
    metrics_retention_days: int = 30


class Settings:
    """Central settings manager."""

    def __init__(self, env: Environment = Environment.DEVELOPMENT):
        self.environment = env
        self.business_hours = BusinessHoursConfig()
        self.sla = SLAConfig()
        self.sentiment = SentimentConfig()
        self.language = LanguageConfig()
        self.session = SessionConfig()
        self.knowledge_base = KnowledgeBaseConfig()
        self.multimodal = MultimodalConfig()
        self.tickets = TicketConfig()
        self.security = SecurityConfig()
        self.monitoring = MonitoringConfig()
        self._runtime_overrides: Dict[str, Any] = {}

    def update_runtime(self, section: str, key: str, value: Any) -> None:
        """Apply runtime configuration override."""
        override_key = f"{section}.{key}"
        self._runtime_overrides[override_key] = value
        if hasattr(self, section):
            config = getattr(self, section)
            if hasattr(config, key):
                setattr(config, key, value)

    def get_runtime_override(self, section: str, key: str) -> Optional[Any]:
        """Get a runtime override value."""
        override_key = f"{section}.{key}"
        return self._runtime_overrides.get(override_key)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize settings to dictionary."""
        import dataclasses
        result = {}
        for attr_name in [
            "business_hours", "sla", "sentiment", "language", "session",
            "knowledge_base", "multimodal", "tickets", "security", "monitoring"
        ]:
            config = getattr(self, attr_name)
            if dataclasses.is_dataclass(config):
                result[attr_name] = dataclasses.asdict(config)
        result["environment"] = self.environment.value
        result["runtime_overrides"] = self._runtime_overrides
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Settings":
        """Deserialize settings from dictionary."""
        env = Environment(data.get("environment", "development"))
        settings = cls(env=env)
        for section_name, section_data in data.items():
            if section_name in ("environment", "runtime_overrides"):
                continue
            if hasattr(settings, section_name):
                config = getattr(settings, section_name)
                for key, value in section_data.items():
                    if hasattr(config, key):
                        setattr(config, key, value)
        for key, value in data.get("runtime_overrides", {}).items():
            section, attr = key.split(".", 1)
            settings.update_runtime(section, attr, value)
        return settings

    @classmethod
    def from_json_file(cls, filepath: str) -> "Settings":
        """Load settings from a JSON file."""
        with open(filepath, "r") as f:
            data = json.load(f)
        return cls.from_dict(data)

    def save_to_json(self, filepath: str) -> None:
        """Save settings to a JSON file."""
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w") as f:
            json.dump(self.to_dict(), f, indent=2, default=str)


# Global singleton
_settings: Optional[Settings] = None


def get_settings(env: Optional[Environment] = None) -> Settings:
    """Get or create global settings instance."""
    global _settings
    if _settings is None or env is not None:
        _settings = Settings(env=env or Environment.DEVELOPMENT)
    return _settings

