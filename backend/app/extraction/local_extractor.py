"""Offline extractor: embedded text layer + word positions. No API, no network.

Reliable on digital PDFs that carry a data block or labelled dimensions. It
reads only what's actually written — anything absent stays "Unable to
determine" rather than guessed. Confidence is high but capped below the vision
backend, because text labels can disagree with the drawn geometry and this
backend does not reconcile them.
"""
import logging
import re
from typing import List, Optional

from . import render
from .schema import (
    FIELD_UNITS,
    BBox,
    Field,
    SitePlan,
    Source,
    undetermined,
)

logger = logging.getLogger(__name__)

# label -> regex capturing the numeric value from the text layer
PATTERNS = {
    "lot_width": r"lot\s*width[:\s]+([\d.]+)",
    "lot_depth": r"lot\s*depth[:\s]+([\d.]+)",
    "lot_area": r"lot\s*area[:\s]+([\d.]+)",
    "building_footprint_width": r"footprint\s*width[:\s]+([\d.]+)",
    "building_footprint_depth": r"footprint\s*depth[:\s]+([\d.]+)",
    "building_footprint_area": r"(?:building\s*)?footprint[:\s]*(?:area)?[:\s]+([\d.]+)\s*sq",
    "building_height": r"building\s*height[:\s]+([\d.]+)",
    "front_setback": r"front\s*setback[:\s]+([\d.]+)",
    "rear_setback": r"rear\s*setback[:\s]+([\d.]+)",
    "parking_stalls": r"parking\s*stalls?[:\s]+(\d+)",
}

# Confidence for a clean regex hit on the embedded text layer.
TEXT_CONFIDENCE = 0.9


class LocalExtractor:
    name = "local"

    def extract(self, pdf_path: str) -> SitePlan:
        text = render.extract_text(pdf_path)
        words = render.extract_words(pdf_path, page=0)
        width_pt, height_pt = render.page_dimensions(pdf_path)

        plan = SitePlan(
            backend=self.name,
            source_pdf=pdf_path,
            page_count=render.page_count(pdf_path),
            page_width_pt=width_pt,
            page_height_pt=height_pt,
        )

        lower = text.lower()
        for key, pattern in PATTERNS.items():
            match = re.search(pattern, lower)
            if not match:
                plan.set(undetermined(key))
                continue
            raw = match.group(1)
            value = float(raw)
            plan.set(Field(
                name=key,
                value=value,
                unit=FIELD_UNITS[key],
                confidence=TEXT_CONFIDENCE,
                source=Source.TEXT,
                bbox=self._locate(words, raw, width_pt, height_pt),
            ))

        # Side setback: take the governing (minimum) of any labelled sides.
        plan.set(self._side_setback(lower, words, width_pt, height_pt))

        plan.warnings.append(
            "Local backend: values read from the text layer only; drawn "
            "geometry is not cross-checked."
        )
        return plan

    def _side_setback(self, lower, words, w, h) -> Field:
        values = [float(v) for v in
                  re.findall(r"side\s*setback[:\s]+([\d.]+)", lower)]
        if not values:
            return undetermined("side_setback")
        governing = min(values)
        return Field(
            name="side_setback",
            value=governing,
            unit=FIELD_UNITS["side_setback"],
            confidence=TEXT_CONFIDENCE,
            source=Source.TEXT,
            bbox=self._locate(words, _fmt(governing), w, h),
            note=("governing (minimum) of multiple side setbacks"
                  if len(values) > 1 else None),
        )

    @staticmethod
    def _locate(words: List[render.Word], value_str: str,
                w: float, h: float) -> Optional[BBox]:
        """Box the first token matching the value, for annotation."""
        for word in words:
            if word.text == value_str:
                return BBox(
                    x0=word.x0 / w, y0=word.top / h,
                    x1=word.x1 / w, y1=word.bottom / h,
                    page=word.page,
                )
        return None


def _fmt(value: float) -> str:
    """Render a float the way it appears in the text (drop trailing .0)."""
    return f"{value:g}"
