"""
Session Manager for Multilingual Chatbot.

Handles customer session lifecycle:
- Isolation of concurrent sessions
- 30-minute inactivity timeout (configurable)
- Restoration of conversation summary if customer returns within 24 hours
- Fresh session initiation if inactive beyond 24 hours
- Fully integrated with TimeProvider for deterministic time simulation in tests
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from src.core.config.settings import get_settings, SessionConfig
from src.core.models.data_models import Message, SessionState
from src.core.utils.helpers import TimeProvider, get_logger

logger = get_logger("multilingual.session_manager")


class SessionManager:
    """
    Manages customer sessions, inactivity expirations, and 24-hour summary restoration.
    """

    def __init__(self, config: Optional[SessionConfig] = None) -> None:
        self.config = config or get_settings().session
        # Active sessions indexed by session_id
        self._sessions_by_id: Dict[str, SessionState] = {}
        # Customer ID to currently active session_id
        self._customer_active_session: Dict[str, str] = {}
        # Historical expired sessions per customer: customer_id -> List[SessionState]
        self._customer_history: Dict[str, List[SessionState]] = {}

    def create_session(self, customer_id: str, language: str = "en") -> SessionState:
        """
        Create a new active session for a customer.
        If customer already had an active session, expire it first.
        """
        now = TimeProvider.now()

        # If previous active session exists, close it
        if customer_id in self._customer_active_session:
            old_sid = self._customer_active_session[customer_id]
            self.expire_session(old_sid)

        session_id = str(uuid.uuid4())
        session = SessionState(
            session_id=session_id,
            customer_id=customer_id,
            current_language=language,
            messages=[],
            context_summary="",
            started_at=now,
            last_activity=now,
            is_active=True,
            expired=False,
        )

        self._sessions_by_id[session_id] = session
        self._customer_active_session[customer_id] = session_id
        logger.info(f"Created new session {session_id} for customer {customer_id}")
        return session

    def get_session(self, session_id: str) -> Optional[SessionState]:
        """Retrieve session by ID, checking for inactivity expiration first."""
        session = self._sessions_by_id.get(session_id)
        if session and session.is_active:
            if self.check_timeout(session_id):
                self.expire_session(session_id)
        return session

    def get_active_session(self, customer_id: str) -> Optional[SessionState]:
        """Get current active session for customer, checking for inactivity timeout."""
        session_id = self._customer_active_session.get(customer_id)
        if not session_id:
            return None

        if self.check_timeout(session_id):
            self.expire_session(session_id)
            return None

        return self._sessions_by_id.get(session_id)

    def update_activity(self, session_id: str) -> None:
        """Update last activity timestamp to current time."""
        session = self._sessions_by_id.get(session_id)
        if session and session.is_active:
            session.last_activity = TimeProvider.now()

    def check_timeout(self, session_id: str) -> bool:
        """
        Check whether a session has exceeded the inactivity threshold.
        Default: 30 minutes.
        """
        session = self._sessions_by_id.get(session_id)
        if not session or not session.is_active:
            return False

        now = TimeProvider.now()
        elapsed_minutes = (now - session.last_activity).total_seconds() / 60.0
        return elapsed_minutes >= self.config.inactivity_timeout_minutes

    def expire_session(self, session_id: str) -> Optional[SessionState]:
        """
        Marks an active session as expired, compiles its context summary,
        and saves it to customer history for potential 24-hour restore.
        """
        session = self._sessions_by_id.get(session_id)
        if not session:
            return None

        session.is_active = False
        session.expired = True

        # Generate summary if not already present
        if not session.context_summary and session.messages:
            user_texts = [m.content for m in session.messages if m.is_customer]
            session.context_summary = f"Prior discussion: {'; '.join(user_texts[-3:])}"

        # Clean active session mapping
        if self._customer_active_session.get(session.customer_id) == session_id:
            del self._customer_active_session[session.customer_id]

        # Record in history
        if session.customer_id not in self._customer_history:
            self._customer_history[session.customer_id] = []
        self._customer_history[session.customer_id].append(session)

        logger.info(f"Expired session {session_id} for customer {session.customer_id}")
        return session

    def restore_session(self, customer_id: str) -> Optional[SessionState]:
        """
        If the customer returns within 24 hours of their last expired session,
        restore a new session pre-populated with the previous session summary.
        If older than 24 hours (or no prior session), return None.
        """
        history = self._customer_history.get(customer_id, [])
        if not history:
            return None

        last_session = history[-1]
        now = TimeProvider.now()
        elapsed_hours = (now - last_session.last_activity).total_seconds() / 3600.0

        if elapsed_hours <= self.config.restore_window_hours:
            new_session = self.create_session(
                customer_id=customer_id,
                language=last_session.current_language,
            )
            new_session.previous_session_summary = last_session.context_summary or "Previous inquiry summary restored."
            logger.info(
                f"Restored session context for customer {customer_id} (elapsed: {elapsed_hours:.1f}h)"
            )
            return new_session

        return None

    def start_new_session(self, customer_id: str, language: str = "en") -> SessionState:
        """
        Starts a brand new session, ignoring previous session summary (used when >24 hours).
        """
        return self.create_session(customer_id=customer_id, language=language)
