"""
File validation for uploaded files.

Checks file format, size, safety (executables, scripts),
prompt injection in text content, and suspicious metadata.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import List, Tuple

from src.core.config.settings import get_settings, MultimodalConfig
from src.core.utils.helpers import detect_prompt_injection, get_logger

logger = get_logger("multimodal.file_validator")

# Extensions considered unsafe / executable
_UNSAFE_EXTENSIONS: set[str] = {
    "exe", "bat", "cmd", "sh", "bash", "ps1", "psm1",
    "vbs", "vbe", "js", "jse", "wsf", "wsh", "msi",
    "scr", "pif", "com", "dll", "sys", "cpl", "inf",
    "reg", "app", "action", "command", "workflow",
}

# Suspicious filename patterns that may indicate hidden instructions
_SUSPICIOUS_FILENAME_PATTERNS: list[str] = [
    r"ignore[\s_-]?instructions",
    r"system[\s_-]?prompt",
    r"admin[\s_-]?override",
    r"bypass[\s_-]?security",
    r"inject",
]

# Max bytes to read from a text file for injection scanning
_MAX_SCAN_BYTES: int = 1_048_576  # 1 MB


class FileValidator:
    """Validates uploaded files for safety and format compliance."""

    def __init__(self, config: MultimodalConfig | None = None) -> None:
        self.config = config or get_settings().multimodal
        self._all_supported: set[str] = set(
            self.config.supported_image_formats
            + self.config.supported_document_formats
        )

    # ------------------------------------------------------------------ #
    #  Public API                                                        #
    # ------------------------------------------------------------------ #

    def validate(self, filepath: str) -> Tuple[bool, List[str]]:
        """Validate a file for safety and format compliance.

        Returns:
            (is_safe, list_of_issues)  – if *is_safe* is ``False`` the file
            must **not** be processed further.
        """
        issues: list[str] = []
        path = Path(filepath)

        # 1. File existence
        if not path.exists():
            issues.append(f"File not found: {filepath}")
            return False, issues

        # 2. Extension check
        ext = self._get_extension(path)
        if not ext:
            issues.append("File has no extension; cannot determine type.")
            return False, issues

        # 3. Unsafe extension check
        if ext in _UNSAFE_EXTENSIONS:
            issues.append(
                f"Unsafe file type detected: .{ext}. "
                "Executable and script files are not allowed."
            )
            return False, issues

        # 4. Supported format check
        if ext not in self._all_supported:
            issues.append(
                f"Unsupported file format: .{ext}. "
                f"Supported formats: {sorted(self._all_supported)}"
            )
            return False, issues

        # 5. File size check
        size_mb = path.stat().st_size / (1024 * 1024)
        if size_mb > self.config.max_file_size_mb:
            issues.append(
                f"File size ({size_mb:.1f} MB) exceeds maximum "
                f"allowed size ({self.config.max_file_size_mb} MB)."
            )
            return False, issues

        # 6. Suspicious filename patterns (simulated EXIF/metadata check)
        filename_lower = path.stem.lower()
        for pattern in _SUSPICIOUS_FILENAME_PATTERNS:
            if re.search(pattern, filename_lower, re.IGNORECASE):
                issues.append(
                    f"Suspicious filename pattern detected: '{path.name}'. "
                    "This may indicate an attempt to embed instructions."
                )
                return False, issues

        # 7. Prompt injection scan for text-based files
        if ext in self.config.supported_document_formats:
            injection_issues = self._scan_text_for_injection(path)
            if injection_issues:
                issues.extend(injection_issues)
                return False, issues

        # Passed all checks
        if issues:
            return False, issues
        return True, []

    # ------------------------------------------------------------------ #
    #  Internal helpers                                                  #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _get_extension(path: Path) -> str:
        """Return lower-cased extension without the dot."""
        ext = path.suffix.lstrip(".")
        return ext.lower()

    @staticmethod
    def _scan_text_for_injection(path: Path) -> list[str]:
        """Read the first MB of a text file and check for prompt injection."""
        issues: list[str] = []
        try:
            with open(path, "r", errors="replace") as fh:
                content = fh.read(_MAX_SCAN_BYTES)
            is_injection, patterns = detect_prompt_injection(content)
            if is_injection:
                issues.append(
                    "Prompt injection attempt detected in file content. "
                    f"Matched {len(patterns)} suspicious pattern(s)."
                )
        except Exception as exc:  # pragma: no cover
            logger.warning("Could not scan file %s for injection: %s", path, exc)
        return issues
