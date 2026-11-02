"""
Data extraction from text content.

Uses ``extract_patterns()`` to pull order IDs, dates, amounts, product codes,
and error codes.  Compares extracted data against the customer's message
content for consistency and flags conflicts.  Never invents missing values.
"""

from __future__ import annotations

from typing import List, Optional

from src.core.config.settings import get_settings
from src.core.models.data_models import FileProcessingResult, FileProcessingStatus, Message
from src.core.utils.helpers import extract_patterns, mask_sensitive_data, get_logger

logger = get_logger("multimodal.data_extractor")


class DataExtractor:
    """Extract structured data from text and detect conflicts with messages."""

    def __init__(self) -> None:
        self.settings = get_settings()

    # ------------------------------------------------------------------ #
    #  Public API                                                        #
    # ------------------------------------------------------------------ #

    def extract(
        self,
        text: str,
        message: Optional[Message] = None,
    ) -> FileProcessingResult:
        """Extract structured data from *text* and optionally cross-check
        against the customer's *message*.

        Returns a populated :class:`FileProcessingResult`.  Fields that
        cannot be found are left as empty lists – **nothing is invented**.
        """
        patterns = extract_patterns(text)

        result = FileProcessingResult(
            status=FileProcessingStatus.COMPLETED,
            extracted_text=text,
            order_ids=patterns.get("order_ids", []),
            dates=patterns.get("dates", []),
            amounts=patterns.get("amounts", []),
            product_info=patterns.get("product_codes", []),
            error_codes=patterns.get("error_codes", []),
        )

        # Store all raw extracted data for downstream consumers
        result.extracted_data = patterns

        # Cross-check against the message
        if message is not None:
            conflicts = self.detect_conflicts(result, message)
            result.conflicts = conflicts

        # Mask PII in the log entry
        result.masked_log_entry = mask_sensitive_data(
            f"Extracted from file: {text[:500]}"
        )

        return result

    def detect_conflicts(
        self,
        extracted: FileProcessingResult,
        message: Message,
    ) -> List[str]:
        """Compare extracted data with the customer message and flag conflicts.

        Checks:
        * Order IDs in file vs. message
        * Amounts in file vs. message
        * Dates in file vs. message

        Returns a list of human-readable conflict descriptions.
        """
        conflicts: list[str] = []
        msg_patterns = extract_patterns(message.content)

        # --- Order ID conflicts ---
        msg_order_ids = set(msg_patterns.get("order_ids", []))
        file_order_ids = set(extracted.order_ids)
        if msg_order_ids and file_order_ids:
            # Normalise for comparison (upper-case)
            msg_norm = {oid.upper() for oid in msg_order_ids}
            file_norm = {oid.upper() for oid in file_order_ids}
            if msg_norm != file_norm and not msg_norm.intersection(file_norm):
                conflicts.append(
                    f"Order ID mismatch: message mentions {sorted(msg_norm)}, "
                    f"but file contains {sorted(file_norm)}."
                )

        # --- Amount conflicts ---
        msg_amounts = self._normalise_amounts(msg_patterns.get("amounts", []))
        file_amounts = self._normalise_amounts(extracted.amounts)
        if msg_amounts and file_amounts:
            if msg_amounts != file_amounts and not msg_amounts.intersection(file_amounts):
                conflicts.append(
                    f"Amount mismatch: message mentions {sorted(msg_amounts)}, "
                    f"but file contains {sorted(file_amounts)}."
                )

        # --- Date conflicts ---
        msg_dates = set(msg_patterns.get("dates", []))
        file_dates = set(extracted.dates)
        if msg_dates and file_dates:
            if msg_dates != file_dates and not msg_dates.intersection(file_dates):
                conflicts.append(
                    f"Date mismatch: message mentions {sorted(msg_dates)}, "
                    f"but file contains {sorted(file_dates)}."
                )

        return conflicts

    # ------------------------------------------------------------------ #
    #  Internal helpers                                                  #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _normalise_amounts(amounts: list[str]) -> set[str]:
        """Normalise amount strings for comparison.

        Strips currency symbols and whitespace, keeps digits and
        decimal separators.
        """
        import re

        normalised: set[str] = set()
        for amt in amounts:
            cleaned = re.sub(r"[^\d.,]", "", amt).strip()
            if cleaned:
                normalised.add(cleaned)
        return normalised
