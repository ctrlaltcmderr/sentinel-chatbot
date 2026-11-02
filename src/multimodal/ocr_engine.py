"""
Simulated OCR engine for text extraction.

For text/PDF files: reads content directly.
For images: simulates OCR by checking file properties and returning
metadata-based results (no external OCR libraries required).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Tuple

from src.core.config.settings import get_settings, MultimodalConfig
from src.core.utils.helpers import get_logger

logger = get_logger("multimodal.ocr_engine")

# Attempt to import optional libraries for richer metadata extraction.
# These are NOT required – the engine falls back gracefully.
try:
    from PIL import Image as PILImage  # type: ignore[import-untyped]
    _HAS_PIL = True
except ImportError:  # pragma: no cover
    _HAS_PIL = False

try:
    import PyPDF2  # type: ignore[import-untyped]
    _HAS_PYPDF2 = True
except ImportError:  # pragma: no cover
    _HAS_PYPDF2 = False


class OCREngine:
    """Simulated OCR / text extraction engine.

    * **Text files** (`.txt`, `.csv`, `.json`): reads content directly.
    * **PDF files**: extracts text from each page via PyPDF2 (if available),
      otherwise reads raw bytes as text.
    * **Image files**: uses Pillow to read dimensions and simulates a quality
      score.  No actual OCR is performed.
    """

    def __init__(self, config: MultimodalConfig | None = None) -> None:
        self.config = config or get_settings().multimodal

    # ------------------------------------------------------------------ #
    #  Public API                                                        #
    # ------------------------------------------------------------------ #

    def extract_text(self, filepath: str) -> Tuple[str, float]:
        """Extract text and quality score from a file.

        Returns:
            (extracted_text, quality_score)
        """
        path = Path(filepath)
        ext = path.suffix.lstrip(".").lower()

        if ext in ("txt", "csv", "json"):
            return self._extract_from_text(path)
        elif ext == "pdf":
            return self._extract_from_pdf(path)
        elif ext in set(self.config.supported_image_formats):
            return self._extract_from_image(path)
        else:
            logger.warning("Unsupported file type for OCR: .%s", ext)
            return "", 0.0

    def assess_quality(self, filepath: str) -> float:
        """Assess image quality score (0.0 – 1.0).

        For images the score is derived from file size and dimensions.
        For non-image files the quality is always 1.0.
        """
        path = Path(filepath)
        ext = path.suffix.lstrip(".").lower()
        if ext not in set(self.config.supported_image_formats):
            return 1.0
        return self._image_quality_score(path)

    # ------------------------------------------------------------------ #
    #  Internal helpers                                                  #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _extract_from_text(path: Path) -> Tuple[str, float]:
        """Read plain-text (or CSV/JSON) content directly."""
        try:
            content = path.read_text(errors="replace")
            return content, 1.0
        except Exception as exc:  # pragma: no cover
            logger.error("Failed to read text file %s: %s", path, exc)
            return "", 0.0

    @staticmethod
    def _extract_from_pdf(path: Path) -> Tuple[str, float]:
        """Extract text from PDF pages."""
        if _HAS_PYPDF2:
            try:
                reader = PyPDF2.PdfReader(str(path))
                pages_text: list[str] = []
                for page in reader.pages:
                    text = page.extract_text()
                    if text:
                        pages_text.append(text)
                combined = "\n".join(pages_text)
                quality = 1.0 if combined.strip() else 0.5
                return combined, quality
            except Exception as exc:
                logger.error("PyPDF2 extraction failed for %s: %s", path, exc)
                return "", 0.3
        else:
            # Fallback: try reading raw bytes as text
            try:
                raw = path.read_text(errors="replace")
                return raw, 0.5
            except Exception:  # pragma: no cover
                return "", 0.3

    def _extract_from_image(self, path: Path) -> Tuple[str, float]:
        """Simulate OCR for image files.

        Extracts any text embedded in EXIF metadata and returns a quality
        score based on dimensions/file size.
        """
        quality = self._image_quality_score(path)

        # Simulated text: we can read image comment / description metadata
        extracted_text = ""
        if _HAS_PIL:
            try:
                with PILImage.open(str(path)) as img:
                    # Some formats embed a text description
                    info = img.info or {}
                    if "comment" in info:
                        extracted_text = (
                            info["comment"].decode("utf-8", errors="replace")
                            if isinstance(info["comment"], bytes)
                            else str(info["comment"])
                        )
                    # PNG text chunks
                    for key in ("Description", "Comment", "Title"):
                        if key in info:
                            val = info[key]
                            if isinstance(val, bytes):
                                val = val.decode("utf-8", errors="replace")
                            extracted_text += " " + str(val)
                    extracted_text = extracted_text.strip()
            except Exception as exc:  # pragma: no cover
                logger.warning("Could not read image metadata for %s: %s", path, exc)

        if not extracted_text:
            extracted_text = f"[Simulated OCR placeholder for {path.name}]"

        return extracted_text, quality

    @staticmethod
    def _image_quality_score(path: Path) -> float:
        """Compute a simulated quality score for an image.

        Heuristic:
        * File size < 5 KB  → very low quality (0.2)
        * Dimensions < 100×100 → low quality (0.3)
        * Otherwise scale up to 1.0 based on size/dims.
        """
        file_size = path.stat().st_size

        if _HAS_PIL:
            try:
                with PILImage.open(str(path)) as img:
                    width, height = img.size
            except Exception:
                width, height = 0, 0
        else:
            width, height = 0, 0

        # Score based on file size (proxy for content richness)
        if file_size < 5_000:
            size_score = 0.2
        elif file_size < 50_000:
            size_score = 0.5
        elif file_size < 500_000:
            size_score = 0.7
        else:
            size_score = 1.0

        # Score based on dimensions
        if width == 0 or height == 0:
            dim_score = size_score  # fall back to size-only
        elif width < 100 or height < 100:
            dim_score = 0.3
        elif width < 500 or height < 500:
            dim_score = 0.6
        else:
            dim_score = 1.0

        # Weighted average
        quality = 0.4 * size_score + 0.6 * dim_score
        return round(quality, 2)
