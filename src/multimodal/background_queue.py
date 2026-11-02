"""
Background processing queue for long-running file tasks.

When file processing exceeds the configured timeout, tasks are moved
to a background queue and the customer is notified.
"""

from __future__ import annotations

import uuid
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional

from src.core.config.settings import get_settings, MultimodalConfig
from src.core.models.data_models import (
    FileProcessingResult,
    FileProcessingStatus,
    Message,
)
from src.core.utils.helpers import TimeProvider, get_logger

logger = get_logger("multimodal.background_queue")


@dataclass
class QueuedTask:
    """Internal representation of a queued processing task."""

    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    filepath: str = ""
    message: Optional[Message] = None
    status: FileProcessingStatus = FileProcessingStatus.QUEUED_BACKGROUND
    enqueued_at: datetime = field(default_factory=TimeProvider.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[FileProcessingResult] = None
    error: Optional[str] = None


class BackgroundQueue:
    """FIFO queue for background file processing."""

    def __init__(self, config: MultimodalConfig | None = None) -> None:
        self.config = config or get_settings().multimodal
        # Ordered dict preserves insertion order (FIFO)
        self._queue: OrderedDict[str, QueuedTask] = OrderedDict()

    # ------------------------------------------------------------------ #
    #  Public API                                                        #
    # ------------------------------------------------------------------ #

    def enqueue(
        self,
        task_id: str,
        filepath: str,
        message: Message,
    ) -> str:
        """Add a task to the background queue.

        Args:
            task_id: unique task identifier (or empty to auto-generate).
            filepath: path to the uploaded file.
            message: the customer message associated with this upload.

        Returns:
            The task ID (useful when auto-generated).
        """
        tid = task_id or str(uuid.uuid4())
        task = QueuedTask(
            task_id=tid,
            filepath=filepath,
            message=message,
            status=FileProcessingStatus.QUEUED_BACKGROUND,
            enqueued_at=TimeProvider.now(),
        )
        self._queue[tid] = task
        logger.info("Task %s enqueued for background processing.", tid)
        return tid

    def process_next(self) -> Optional[FileProcessingResult]:
        """Process (simulate) the next queued task.

        In production this would hand off to a worker; here we simply
        mark the oldest queued task as completed and return a stub result.
        """
        for tid, task in self._queue.items():
            if task.status == FileProcessingStatus.QUEUED_BACKGROUND:
                task.status = FileProcessingStatus.PROCESSING
                task.started_at = TimeProvider.now()

                # Simulated processing – in production the actual
                # extraction pipeline would run here.
                result = FileProcessingResult(
                    original_filename=task.filepath,
                    status=FileProcessingStatus.COMPLETED,
                    queued_for_background=True,
                )
                task.result = result
                task.status = FileProcessingStatus.COMPLETED
                task.completed_at = TimeProvider.now()
                logger.info("Task %s processed from background queue.", tid)
                return result

        logger.debug("No tasks in the background queue.")
        return None

    def get_status(self, task_id: str) -> FileProcessingStatus:
        """Return the current status of a queued task.

        If the task is unknown, returns ``PENDING``.
        """
        task = self._queue.get(task_id)
        if task is None:
            return FileProcessingStatus.PENDING
        return task.status

    def get_task(self, task_id: str) -> Optional[QueuedTask]:
        """Return the full task object (or ``None``)."""
        return self._queue.get(task_id)

    def notify_customer(self, task_id: str) -> str:
        """Generate a customer-facing notification message."""
        task = self._queue.get(task_id)
        if task is None:
            return (
                "We couldn't find information about your file. "
                "Please try uploading again."
            )

        if task.status == FileProcessingStatus.QUEUED_BACKGROUND:
            return (
                "Your file is being processed. "
                "We'll update you shortly."
            )
        elif task.status == FileProcessingStatus.PROCESSING:
            return (
                "Your file is currently being processed. "
                "We'll update you shortly."
            )
        elif task.status == FileProcessingStatus.COMPLETED:
            return (
                "Your file has been processed successfully. "
                "Here are the results."
            )
        elif task.status == FileProcessingStatus.FAILED:
            return (
                "We encountered an issue processing your file. "
                "Please try uploading again or contact support."
            )
        else:
            return (
                "Your file is being processed. "
                "We'll update you shortly."
            )

    @property
    def pending_count(self) -> int:
        """Number of tasks still waiting to be processed."""
        return sum(
            1
            for t in self._queue.values()
            if t.status == FileProcessingStatus.QUEUED_BACKGROUND
        )

    @property
    def queue_size(self) -> int:
        """Total tasks in the queue (all statuses)."""
        return len(self._queue)
