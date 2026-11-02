"""
Query Intent Classifier & Semantic Relevance Analyzer for RAG.

Identifies user query intents:
- ORDER_TRACKING: Customer questions regarding order status, location, shipment arrival, or delay.
- WARRANTY: Hardware warranty terms, coverage duration, repair/replacement conditions.
- RETURN_REFUND: Return windows, refund policies, product condition requirements.
- ACCOUNT_SECURITY: Compromised accounts, unauthorized access, password resets.
- BILLING: Invoices, payment charges, double billing.
- GENERAL_POLICY: Other company knowledge base questions.
- OUT_OF_SCOPE: Questions unrelated to support domain.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set

from ..core.models.data_models import KnowledgeDocument
from ..core.utils.helpers import get_logger

logger = get_logger("rag.query_intent")


class QueryIntent(str, Enum):
    ORDER_TRACKING = "order_tracking"
    WARRANTY = "warranty"
    RETURN_REFUND = "return_refund"
    ACCOUNT_SECURITY = "account_security"
    BILLING = "billing"
    GENERAL_POLICY = "general_policy"
    OUT_OF_SCOPE = "out_of_scope"


@dataclass
class QueryIntentResult:
    intent: QueryIntent
    confidence: float
    order_id: Optional[str] = None
    missing_info: List[str] = field(default_factory=list)
    keywords: Set[str] = field(default_factory=set)


# Intent patterns
_ORDER_TRACKING_PATTERNS = [
    r"\bwhere('s|\s+is|\s+are)\s+(my|the|this)?\s*(order|package|delivery|shipment|parcel|item)\b",
    r"\btrack(ing)?\s+(my|the|an)?\s*(order|package|shipment|delivery|parcel)\b",
    r"\b(order|delivery|package|shipment|parcel)\s+(status|tracking|location|update|delayed|delay|late|lost)\b",
    r"\bwhen\s+will\s+(my|the|this)?\s*(order|package|delivery|shipment|parcel)\s+(arrive|come|be\s+delivered)\b",
    r"\bsupposed\s+to\s+arrive\b",
    r"\bhas\s+(my|the)?\s*(order|package|shipment)\s+shipped\b",
    r"\bstatus\s+of\s+(my|the)?\s*order\b",
    r"\bcheck\s+(my|the)?\s*(order|shipment|delivery)\b",
    r"\b(delayed|lost|missing)\s+(order|package|delivery|shipment|parcel)\b",
    r"\bwhere\s+is\s+my\s+parcel\b",
]

_WARRANTY_PATTERNS = [
    r"\bwarrant(y|ies)\b",
    r"\bguarantee\b",
    r"\bhardware\s+(defect|damage|issue|failure)\b",
    r"\baccidental\s+damage\b",
    r"\bliquid\s+damage\b",
    r"\bdrop\s+damage\b",
    r"\brepair\s+coverage\b",
    r"\breplacement\s+warranty\b",
    r"\bdeductible\b",
    r"\bon-site\s+warranty\b",
]

_RETURN_REFUND_PATTERNS = [
    r"\brefund(s|ed|ing)?\b",
    r"\breturn\s+(?:and\s+refund\s+)?(policy|window|item|product|package|guidelines)\b",
    r"\breturn(s|ing)?\b",
    r"\b(get|request|ask\s+for|want)\s+(a\s+)?refund\b",
    r"\bfull\s+refund\b",
    r"\bmoney\s+back\b",
    r"\breimburse(ment)?\b",
    r"\bsend\s+(it\s+)?back\b",
    r"\bhow\s+many\s+days\s+to\s+return\b",
    r"\bcan\s+i\s+return\b",
    r"\bnon-refundable\b",
    r"\breturnable\b",
    r"\brestocking\s+fee\b",
]


_SECURITY_PATTERNS = [
    r"\bunauthorized\s+access\b",
    r"\bcompromise(d)?\b",
    r"\bhack(ed)?\b",
    r"\bsecurity\s+protocol\b",
    r"\bsuspicious\s+(login|activity|transaction)\b",
    r"\baccount\s+takeover\b",
    r"\bstolen\s+credentials\b",
]

_BILLING_PATTERNS = [
    r"\bduplicate\s+payment\b",
    r"\bdouble\s+charg(e|ed)\b",
    r"\bcharged\s+twice\b",
    r"\binvoice\b",
    r"\bbilling\s+(statement|dispute|issue)\b",
    r"\bsettlement\s+playbook\b",
]

# Order ID extraction pattern (e.g., ORD-12345, ORD-998877, Order #12345)
_ORDER_ID_PATTERN = re.compile(
    r"\b(?:ORD-|ORDER-|#)?([A-Za-z]{3,4}-[0-9A-Za-z]{3,10}|ORD[0-9]{4,10})\b|\bORD-([A-Za-z0-9-]+)\b",
    re.IGNORECASE,
)


def extract_order_id(text: str) -> Optional[str]:
    """Extract standard Order ID from customer message."""
    # Look for explicit ORD- prefix
    match = re.search(r"\b(ORD-[A-Za-z0-9]+)\b", text, re.IGNORECASE)
    if match:
        return match.group(1).upper()

    # Look for "order #12345" or "order number 12345" or "order 12345"
    match2 = re.search(r"\border\s*(?:#|id|number|no\.?)?[:\s]*#?([A-Za-z0-9-]{4,12})\b", text, re.IGNORECASE)
    if match2:
        candidate = match2.group(1).strip()
        # Must contain digits or start with ord
        if not re.search(r"\d", candidate) and not candidate.lower().startswith("ord"):
            return None
        stopwords_avoid = {
            "yesterday", "status", "today", "tomorrow", "tracking", "delayed", "late",
            "details", "reference", "number", "update", "online", "retail", "package",
            "delivery", "shipment", "items", "issue", "history", "support", "cancel",
            "warranty", "refund", "return", "policy", "laptop", "product",
        }
        if candidate.lower() not in stopwords_avoid:
            return candidate.upper() if candidate.startswith("ord") else f"ORD-{candidate.upper()}"

    return None


def classify_query_intent(query: str, context: Optional[Dict[str, Any]] = None) -> QueryIntentResult:
    """
    Classify the query intent and extract domain entities.
    Checks specific policy intents (Warranty, Refund, Security, Billing) and
    transactional intents (Order Tracking) accurately.
    """
    q_lower = query.lower().strip()
    order_id = extract_order_id(query)

    # 1. Warranty Queries
    for pattern in _WARRANTY_PATTERNS:
        if re.search(pattern, q_lower):
            return QueryIntentResult(
                intent=QueryIntent.WARRANTY,
                confidence=0.95,
                keywords={"warranty", "hardware", "coverage", "repair", "defect"},
            )

    # 2. Return & Refund Queries
    for pattern in _RETURN_REFUND_PATTERNS:
        if re.search(pattern, q_lower):
            return QueryIntentResult(
                intent=QueryIntent.RETURN_REFUND,
                confidence=0.95,
                keywords={"return", "refund", "money", "packaging", "policy"},
            )

    # 3. Account Security Queries
    for pattern in _SECURITY_PATTERNS:
        if re.search(pattern, q_lower):
            return QueryIntentResult(
                intent=QueryIntent.ACCOUNT_SECURITY,
                confidence=0.95,
                keywords={"security", "compromise", "unauthorized", "protocol"},
            )

    # 4. Billing & Invoices
    for pattern in _BILLING_PATTERNS:
        if re.search(pattern, q_lower):
            return QueryIntentResult(
                intent=QueryIntent.BILLING,
                confidence=0.90,
                keywords={"invoice", "billing", "payment", "charge"},
            )

    # 5. Order Tracking Queries
    for pattern in _ORDER_TRACKING_PATTERNS:
        if re.search(pattern, q_lower):
            missing = [] if order_id else ["order_id"]
            return QueryIntentResult(
                intent=QueryIntent.ORDER_TRACKING,
                confidence=0.95,
                order_id=order_id,
                missing_info=missing,
                keywords={"order", "tracking", "delivery", "shipping", "status"},
            )

    # If query provided an order ID with an order-related word
    if order_id and any(w in q_lower for w in ["order", "ord", "package", "delivery", "track", "shipment", "parcel"]):
        return QueryIntentResult(
            intent=QueryIntent.ORDER_TRACKING,
            confidence=0.95,
            order_id=order_id,
            missing_info=[],
            keywords={"order", "tracking", "delivery"},
        )

    # If query mentions "order" combined with tracking/delivery keywords
    if "order" in q_lower and any(w in q_lower for w in ["where", "track", "status", "arrive", "shipped", "delivery", "parcel", "package", "yesterday", "late", "when"]):
        missing = [] if order_id else ["order_id"]
        return QueryIntentResult(
            intent=QueryIntent.ORDER_TRACKING,
            confidence=0.90,
            order_id=order_id,
            missing_info=missing,
            keywords={"order", "tracking", "delivery"},
        )

    # 6. Default to general policy
    return QueryIntentResult(
        intent=QueryIntent.GENERAL_POLICY,
        confidence=0.50,
        order_id=order_id,
        keywords=set(re.findall(r"\b[a-z]{3,}\b", q_lower)),
    )



def is_document_relevant_to_intent(doc: KnowledgeDocument, intent: QueryIntent) -> bool:
    """
    Verify whether a retrieved document's domain aligns with the query intent.
    Strictly prevents cross-domain pollution (e.g. warranty documents returned for refund or order queries).
    """
    # Order tracking should NEVER match static legal policies
    if intent == QueryIntent.ORDER_TRACKING:
        return False

    title_lower = doc.title.lower()
    content_lower = doc.content.lower()
    tags_lower = " ".join(doc.tags).lower()
    doc_text = f"{title_lower} {content_lower} {tags_lower}"

    if intent == QueryIntent.WARRANTY:
        warranty_terms = ["warranty", "hardware", "defect", "repair", "accidental damage", "on-site", "deductible"]
        return any(term in doc_text for term in warranty_terms)

    if intent == QueryIntent.RETURN_REFUND:
        refund_terms = ["return", "refund", "money back", "reimbursement", "packaging", "30 days", "non-refundable"]
        # Must have refund/return terms AND not be solely a warranty document
        has_refund = any(term in doc_text for term in refund_terms)
        is_pure_warranty = "warranty" in title_lower and not ("return" in title_lower or "refund" in title_lower)
        return has_refund and not is_pure_warranty

    if intent == QueryIntent.ACCOUNT_SECURITY:
        security_terms = ["security", "compromise", "unauthorized", "protocol", "audit", "password", "session"]
        return any(term in doc_text for term in security_terms)

    if intent == QueryIntent.BILLING:
        billing_terms = ["billing", "payment", "invoice", "charge", "settlement", "fee", "cost"]
        return any(term in doc_text for term in billing_terms)

    # General policy queries: accept if not conflicting
    return True
