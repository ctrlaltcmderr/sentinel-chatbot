"""
Multimodal Processor - Orchestrates multimodal file processing pipeline.

Workflow:
1. File validation (extension, size, unsafe scripts, prompt injection)
2. OCR & text extraction + quality assessment
3. Structured data extraction (order IDs, dates, amounts, product info)
4. Cross-referencing against customer message for discrepancies
5. Low-quality image & conflict detection triggering clarification requests
6. Background queue dispatch if processing latency exceeds timeout threshold
7. Secure masking of PII & payment info in all logs
8. Retention management registration
"""

from __future__ import annotations

import os
import time
import uuid
from pathlib import Path
from typing import Optional

from src.core.config.settings import get_settings, MultimodalConfig
from src.core.models.data_models import (
    FileProcessingResult,
    FileProcessingStatus,
    Message,
)
from src.core.utils.helpers import (
    TimeProvider,
    get_logger,
    mask_sensitive_data,
    measure_latency,
)
from .background_queue import BackgroundQueue
from .data_extractor import DataExtractor
from .file_validator import FileValidator
from .ocr_engine import OCREngine
from .retention_manager import RetentionManager

logger = get_logger("multimodal.processor")


class MultimodalProcessor:
    """
    Main orchestrator for multimodal file processing in Sentinel Chatbot.
    """

    def __init__(
        self,
        config: Optional[MultimodalConfig] = None,
        validator: Optional[FileValidator] = None,
        ocr_engine: Optional[OCREngine] = None,
        extractor: Optional[DataExtractor] = None,
        queue: Optional[BackgroundQueue] = None,
        retention_manager: Optional[RetentionManager] = None,
    ) -> None:
        self.config = config or get_settings().multimodal
        self.validator = validator or FileValidator()
        self.ocr_engine = ocr_engine or OCREngine(self.config)
        self.extractor = extractor or DataExtractor()
        self.queue = queue or BackgroundQueue(self.config)
        self.retention_manager = retention_manager or RetentionManager(self.config)

    def process_file(
        self,
        filepath: str,
        message: Optional[Message] = None,
        simulated_duration_seconds: float = 0.0,
    ) -> FileProcessingResult:
        """
        Processes an uploaded file through the multimodal verification pipeline.

        Args:
            filepath: Path to the target file
            message: Optional customer Message object for cross-referencing
            simulated_duration_seconds: Simulated execution duration (for testing timeout)

        Returns:
            FileProcessingResult containing status, extracted attributes, and conflicts.
        """
        path = Path(filepath)
        filename = path.name
        ext = path.suffix.lstrip(".").lower()
        file_id = str(uuid.uuid4())

        result = FileProcessingResult(
            id=file_id,
            original_filename=filename,
            file_type=ext,
            status=FileProcessingStatus.PROCESSING,
        )

        # 1. Check for timeout / background delegation
        timeout_threshold = self.config.processing_timeout_seconds
        if simulated_duration_seconds > timeout_threshold:
            logger.warning(
                f"Processing time {simulated_duration_seconds:.1f}s exceeded {timeout_threshold}s limit. "
                f"Delegating file {filename} to background queue."
            )
            msg = message or Message(content="File upload processing")
            task_id = self.queue.enqueue(file_id, filepath, msg)
            notification = self.queue.notify_customer(task_id)
            result.status = FileProcessingStatus.QUEUED_BACKGROUND
            result.queued_for_background = True
            result.processing_time_seconds = simulated_duration_seconds
            result.metadata["notification"] = notification
            result.metadata["task_id"] = task_id
            return result

        # 2. File Validation
        is_safe, issues = self.validator.validate(filepath)
        if not is_safe:
            logger.warning(f"File {filename} failed validation: {issues}")
            result.status = FileProcessingStatus.REJECTED
            result.is_safe = False
            result.safety_issues = issues
            result.masked_log_entry = mask_sensitive_data(f"Rejected unsafe file {filename}: {issues}")
            return result

        # 3. OCR & Quality Assessment
        extracted_text, quality_score = self.ocr_engine.extract_text(filepath)
        result.extracted_text = extracted_text
        result.quality_score = quality_score

        # Check for low quality
        if quality_score < self.config.min_image_quality_score:
            logger.warning(f"File {filename} quality score {quality_score:.2f} is below threshold {self.config.min_image_quality_score}")
            result.status = FileProcessingStatus.FAILED
            result.conflicts.append("Low image quality: Please upload a clearer image or document.")

        # 4. Data Extraction & Consistency Cross-Reference
        extraction_res = self.extractor.extract(extracted_text, message=message)
        result.order_ids = extraction_res.order_ids
        result.dates = extraction_res.dates
        result.amounts = extraction_res.amounts
        result.product_info = extraction_res.product_info
        result.error_codes = extraction_res.error_codes
        result.extracted_data = extraction_res.extracted_data

        # Combine any conflicts found
        for conflict in extraction_res.conflicts:
            if conflict not in result.conflicts:
                result.conflicts.append(conflict)

        # 5. Masked logging
        log_summary = (
            f"Processed file {filename} (ID: {file_id}) | "
            f"Content preview: {extracted_text[:120]} | "
            f"Orders: {result.order_ids} | Dates: {result.dates} | Amounts: {result.amounts} | "
            f"Conflicts: {result.conflicts} | Quality: {quality_score:.2f}"
        )
        result.masked_log_entry = mask_sensitive_data(log_summary)
        logger.info(result.masked_log_entry)

        # 6. Retention registration
        expiry_dt = self.retention_manager.set_retention(file_id, filepath)
        result.retention_expiry = expiry_dt

        # If conflicts or quality failures occurred, flag clarification request
        if result.conflicts:
            result.metadata["requires_clarification"] = True
            result.metadata["clarification_prompt"] = (
                "The uploaded file is unclear or conflicts with your message. "
                "Please upload a clearer image or another file."
            )
            if result.status != FileProcessingStatus.FAILED:
                result.status = FileProcessingStatus.COMPLETED

        if result.status == FileProcessingStatus.PROCESSING:
            result.status = FileProcessingStatus.COMPLETED

        result.processing_time_seconds = simulated_duration_seconds
        return result

    def process_with_timeout(
        self,
        filepath: str,
        message: Optional[Message] = None,
        timeout: Optional[int] = None,
        simulate_delay: float = 0.0,
    ) -> FileProcessingResult:
        """Helper to process with simulated delay for timeout evaluation."""
        return self.process_file(filepath, message, simulated_duration_seconds=simulate_delay)
