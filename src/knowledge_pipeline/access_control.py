"""
Access Controller – role-based document access and audit logging.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from ..core.models.data_models import AccessLevel, KnowledgeDocument
from ..core.utils.helpers import TimeProvider, get_logger

logger = get_logger("knowledge_pipeline.access_control")

# Role hierarchy: higher roles inherit access from lower roles.
_ROLE_HIERARCHY: Dict[str, int] = {
    "public": 0,
    "staff": 1,
    "manager": 2,
    "admin": 3,
}

# Minimum role rank required for each access level
_ACCESS_REQUIREMENTS: Dict[AccessLevel, int] = {
    AccessLevel.PUBLIC: 0,       # everyone
    AccessLevel.INTERNAL: 1,     # staff and above
    AccessLevel.RESTRICTED: 2,   # managers and above
    AccessLevel.CONFIDENTIAL: 3, # admins only
}


class AccessController:
    """Enforce role-based access control on knowledge documents."""

    def __init__(self):
        self._audit_log: List[Dict] = []

    # ── public API ────────────────────────────────────────────────

    def check_access(self, user_role: str, document: KnowledgeDocument) -> bool:
        """Return True if *user_role* is authorised to access *document*.

        Access rules:
        - ``public`` documents → all roles
        - ``internal`` documents → staff, manager, admin
        - ``restricted`` documents → manager, admin
        - ``confidential`` documents → admin only
        """
        role_rank = _ROLE_HIERARCHY.get(user_role.lower(), -1)
        required_rank = _ACCESS_REQUIREMENTS.get(document.access_level, 999)
        granted = role_rank >= required_rank

        if not granted:
            logger.warning(
                "Access DENIED: role=%s, doc=%s (access_level=%s)",
                user_role,
                document.id,
                document.access_level.value,
            )
        return granted

    def audit_access(
        self,
        user_id: str,
        doc_id: str,
        action: str,
        granted: bool,
    ) -> None:
        """Record an access attempt in the audit log."""
        entry = {
            "user_id": user_id,
            "doc_id": doc_id,
            "action": action,
            "granted": granted,
            "timestamp": TimeProvider.now().isoformat(),
        }
        self._audit_log.append(entry)
        level = "info" if granted else "warning"
        getattr(logger, level)(
            "Audit: user=%s doc=%s action=%s granted=%s",
            user_id,
            doc_id,
            action,
            granted,
        )

    def get_audit_log(self) -> List[Dict]:
        """Return the full audit log."""
        return list(self._audit_log)

    def get_user_audit(self, user_id: str) -> List[Dict]:
        """Return audit entries for a specific user."""
        return [e for e in self._audit_log if e["user_id"] == user_id]
