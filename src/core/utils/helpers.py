"""
Core utilities shared across all Sentinel Chatbot components.
"""

from __future__ import annotations

import hashlib
import re
import uuid
import logging
import time
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Tuple

from ..config.settings import get_settings


# ──────────────────────────── Logging ────────────────────────────

def get_logger(name: str) -> logging.Logger:
    """Get a configured logger."""
    logger = logging.getLogger(f"sentinel.{name}")
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s | %(name)s | %(levelname)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        settings = get_settings()
        logger.setLevel(getattr(logging, settings.monitoring.log_level, logging.INFO))
    return logger


# ──────────────────────────── Security Utilities ────────────────────────────

def mask_sensitive_data(text: str) -> str:
    """Mask PII and sensitive data in text for logging."""
    settings = get_settings()
    masked = text
    for pattern in settings.security.sensitive_patterns:
        masked = re.sub(pattern, "***MASKED***", masked, flags=re.IGNORECASE)
    return masked


def detect_prompt_injection(text: str) -> Tuple[bool, List[str]]:
    """Detect prompt injection attempts in text."""
    settings = get_settings()
    detected = []
    for pattern in settings.security.prompt_injection_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            detected.append(pattern)
    return len(detected) > 0, detected


def compute_hash(content: str) -> str:
    """Compute SHA-256 hash of content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def generate_id() -> str:
    """Generate a unique identifier."""
    return str(uuid.uuid4())


# ──────────────────────────── Time Utilities ────────────────────────────

class TimeProvider:
    """
    Pluggable time provider for testing.
    Allows simulating time changes in tests.
    """
    _instance = None
    _mock_time: Optional[datetime] = None

    @classmethod
    def get_instance(cls) -> "TimeProvider":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def now(cls) -> datetime:
        instance = cls.get_instance()
        if instance._mock_time is not None:
            return instance._mock_time
        return datetime.now()

    @classmethod
    def set_mock_time(cls, dt: datetime) -> None:
        """Set a mock time for testing."""
        instance = cls.get_instance()
        instance._mock_time = dt

    @classmethod
    def advance_time(cls, **kwargs) -> None:
        """Advance mock time by given timedelta kwargs."""
        instance = cls.get_instance()
        if instance._mock_time is None:
            instance._mock_time = datetime.utcnow()
        instance._mock_time += timedelta(**kwargs)

    @classmethod
    def reset(cls) -> None:
        """Reset to real time."""
        instance = cls.get_instance()
        instance._mock_time = None


def calculate_business_hours_elapsed(
    start: datetime, end: datetime,
    exclude_weekends: bool = True,
    exclude_holidays: bool = True
) -> float:
    """Calculate elapsed business hours between two datetimes."""
    settings = get_settings()
    bh = settings.business_hours

    total_hours = 0.0
    current = start
    business_start = current.replace(
        hour=bh.start_hour, minute=bh.start_minute, second=0, microsecond=0
    )
    business_end = current.replace(
        hour=bh.end_hour, minute=bh.end_minute, second=0, microsecond=0
    )
    daily_hours = (bh.end_hour - bh.start_hour) + (bh.end_minute - bh.start_minute) / 60.0

    while current.date() <= end.date():
        date_str = current.strftime("%Y-%m-%d")
        is_weekend = exclude_weekends and current.weekday() in bh.weekends
        is_holiday = exclude_holidays and date_str in bh.holidays

        if not is_weekend and not is_holiday:
            day_start = max(
                current,
                current.replace(hour=bh.start_hour, minute=bh.start_minute, second=0)
            )
            day_end = min(
                end,
                current.replace(hour=bh.end_hour, minute=bh.end_minute, second=0)
            )
            if day_start < day_end:
                total_hours += (day_end - day_start).total_seconds() / 3600.0

        current = (current + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

    return max(0.0, total_hours)


# ──────────────────────────── Text Utilities ────────────────────────────

def extract_patterns(text: str) -> Dict[str, List[str]]:
    """Extract common patterns from text (order IDs, dates, amounts, etc.)."""
    patterns = {
        "order_ids": re.findall(r"(?:ORD|ORDER|#)[-\s]?(\w{6,20})", text, re.IGNORECASE),
        "dates": re.findall(
            r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2})\b", text
        ),
        "amounts": re.findall(
            r"[\$€£₹]\s*\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?|[\$€£₹]\s*\d+(?:\.\d{1,2})?|\d+(?:[.,]\d{1,2})?\s*(?:USD|EUR|GBP|INR)",
            text, re.IGNORECASE
        ),
        "emails": re.findall(
            r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text
        ),
        "phone_numbers": re.findall(
            r"(?:\+\d{1,3}[-\s]?)?\(?\d{3}\)?[-\s]?\d{3}[-\s]?\d{4}", text
        ),
        "error_codes": re.findall(
            r"(?:ERR|ERROR|CODE)[-_\s]?([A-Z0-9]{3,10})", text, re.IGNORECASE
        ),
        "product_codes": re.findall(
            r"(?:SKU|PROD|ITEM)[-_\s]?([A-Z0-9]{4,15})", text, re.IGNORECASE
        ),
    }
    return {k: v for k, v in patterns.items() if v}


def normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    return text


def truncate_text(text: str, max_length: int = 500) -> str:
    """Truncate text to max length with ellipsis."""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


# ──────────────────────────── Performance Monitoring ────────────────────────────

def measure_latency(func: Callable) -> Callable:
    """Decorator to measure function execution latency."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        try:
            result = func(*args, **kwargs)
            latency = (time.time() - start) * 1000  # ms
            logger = get_logger("performance")
            settings = get_settings()
            if latency > settings.monitoring.latency_critical_ms:
                logger.critical(f"{func.__name__} took {latency:.0f}ms (CRITICAL)")
            elif latency > settings.monitoring.latency_warning_ms:
                logger.warning(f"{func.__name__} took {latency:.0f}ms (WARNING)")
            return result
        except Exception as e:
            latency = (time.time() - start) * 1000
            logger = get_logger("performance")
            logger.error(f"{func.__name__} failed after {latency:.0f}ms: {e}")
            raise
    return wrapper


class RetryHandler:
    """Handle retries with configurable intervals."""

    def __init__(self, intervals_minutes: Optional[List[int]] = None):
        self.intervals = intervals_minutes or [15, 30, 60]
        self.attempt = 0
        self.logger = get_logger("retry")

    def should_retry(self) -> bool:
        return self.attempt < len(self.intervals)

    def get_wait_minutes(self) -> int:
        if self.attempt < len(self.intervals):
            return self.intervals[self.attempt]
        return self.intervals[-1]

    def record_attempt(self, success: bool, error: Optional[str] = None) -> None:
        self.attempt += 1
        if success:
            self.logger.info(f"Retry attempt {self.attempt} succeeded")
        else:
            self.logger.warning(
                f"Retry attempt {self.attempt} failed: {error}. "
                f"Next retry in {self.get_wait_minutes()} minutes"
                if self.should_retry() else f"No more retries."
            )

    def reset(self) -> None:
        self.attempt = 0

