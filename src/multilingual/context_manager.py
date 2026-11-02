"""
Context Manager for Multilingual Conversations.

Retains conversation context (default 10 messages), tracks language switching,
extracts and handles corrected information (e.g. "Actually my order is ORD-456"),
and generates conversation summaries.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional

from src.core.config.settings import get_settings
from src.core.models.data_models import ConversationContext, Message
from src.core.utils.helpers import extract_patterns, get_logger, mask_sensitive_data

logger = get_logger("multilingual.context_manager")


class ContextManager:
    """
    Manages multi-turn conversation context across language switches and corrections.
    """

    def __init__(self, max_context_messages: int = 10) -> None:
        self.settings = get_settings()
        self.max_context_messages = max_context_messages or self.settings.session.max_context_messages
        # Map of session_id -> List[Message]
        self._history: Dict[str, List[Message]] = {}
        # Map of session_id -> Dict of tracked entities/corrections
        self._entities: Dict[str, Dict[str, str]] = {}
        # Map of session_id -> list of detected languages
        self._language_history: Dict[str, List[str]] = {}

    def add_message(self, session_id: str, message: Message) -> None:
        """
        Add a message to the session context, update language history, and detect corrections.
        """
        if session_id not in self._history:
            self._history[session_id] = []
            self._entities[session_id] = {}
            self._language_history[session_id] = []

        self._history[session_id].append(message)

        if message.language and (
            not self._language_history[session_id] or self._language_history[session_id][-1] != message.language
        ):
            self._language_history[session_id].append(message.language)

        # Detect corrections in the message
        self._detect_and_apply_corrections(session_id, message.content)

        # Also extract patterns into entities
        extracted = extract_patterns(message.content)
        if "order_ids" in extracted and extracted["order_ids"]:
            self._entities[session_id]["order_id"] = extracted["order_ids"][-1]
        if "product_codes" in extracted and extracted["product_codes"]:
            self._entities[session_id]["product_code"] = extracted["product_codes"][-1]

    def get_context(self, session_id: str, max_messages: Optional[int] = None) -> List[Message]:
        """
        Retrieve the latest N messages from the session context (default 10).
        """
        limit = max_messages if max_messages is not None else self.max_context_messages
        history = self._history.get(session_id, [])
        return history[-limit:] if limit > 0 else history

    def get_latest_language(self, session_id: str) -> str:
        """Get the most recently detected language for the session."""
        languages = self._language_history.get(session_id, [])
        return languages[-1] if languages else "en"

    def get_tracked_entities(self, session_id: str) -> Dict[str, str]:
        """Get all currently tracked entities for the session, accounting for corrections."""
        return self._entities.get(session_id, {}).copy()

    def _detect_and_apply_corrections(self, session_id: str, text: str) -> None:
        """
        Identify correction statements such as:
        - "Actually, my order ID is ORD-999, not ORD-111"
        - "I meant ORD-999"
        - "Correction: my email is user@example.com"
        """
        lower = text.lower()
        patterns = [
            r"(?:actually|i meant|correction|not [^\s,]+ but|wait,?\s*(?:my)?)\s*(?:is\s*)?([a-zA-Z0-9_\-\.\@]+)",
            r"(?:actually|i meant)\s*,?\s*(?:my\s+order\s+(?:id|number)?\s*(?:is)?\s*)([A-Za-z0-9\-_]+)",
        ]

        for pat in patterns:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                corrected_val = match.group(1).strip()
                # Determine entity type
                if re.match(r"(?:ORD|ORDER|#)[-\s]?[a-zA-Z0-9]+", corrected_val, re.IGNORECASE) or (
                    len(corrected_val) >= 4 and corrected_val.isalnum()
                ):
                    self._entities[session_id]["order_id"] = corrected_val
                    logger.info(f"Session {session_id}: Corrected order_id to {corrected_val}")
                elif "@" in corrected_val:
                    self._entities[session_id]["email"] = corrected_val
                    logger.info(f"Session {session_id}: Corrected email to {corrected_val}")

    def get_summary(self, session_id: str) -> str:
        """
        Generate a concise summary of the conversation context.
        """
        messages = self._history.get(session_id, [])
        if not messages:
            return "No messages in session."

        entities = self._entities.get(session_id, {})
        user_msgs = [m.content for m in messages if m.is_customer]
        last_user_query = user_msgs[-1] if user_msgs else "N/A"

        summary_parts = [
            f"Total Messages: {len(messages)}",
            f"Languages Used: {', '.join(set(self._language_history.get(session_id, ['en'])))}",
            f"Last User Inquiry: {last_user_query[:100]}",
        ]
        if entities:
            entity_str = ", ".join(f"{k}: {v}" for k, v in entities.items())
            summary_parts.append(f"Entities: {entity_str}")

        return " | ".join(summary_parts)

    def clear(self, session_id: str) -> None:
        """Clear context for session."""
        self._history.pop(session_id, None)
        self._entities.pop(session_id, None)
        self._language_history.pop(session_id, None)
