"""Shared helpers for the vision extractor(s).

A vision backend reads a rendered page, returns a per-field shape, and then
reconciles its readings against the PDF text layer. That mapping and cross-check
is backend-agnostic, so it lives here and the extractor just calls it.
"""
import re
from typing import Optional

from .local_extractor import PATTERNS as TEXT_PATTERNS
from .schema import FIELD_UNITS, BBox, Field, SitePlan, Source, undetermined


def to_field(key: str, data: Optional[dict]) -> Field:
    """Map one raw field from a vision model into a SitePlan Field.

    A missing value becomes an honest "Unable to determine" rather than a guess.
    """
    if not data or data.get("value") is None:
        note = (data or {}).get("note") or "Unable to determine"
        return undetermined(key, note)
    bbox = None
    b = data.get("bbox")
    if b and all(b.get(k) is not None for k in ("x0", "y0", "x1", "y1")):
        bbox = BBox(x0=b["x0"], y0=b["y0"], x1=b["x1"], y1=b["y1"])
    return Field(
        name=key,
        value=float(data["value"]),
        unit=FIELD_UNITS[key],
        confidence=float(data.get("confidence", 0.5)),
        source=Source.VISION,
        bbox=bbox,
        note=data.get("note"),
    )


def cross_check(plan: SitePlan, text: str) -> None:
    """Reconcile vision readings with the embedded text layer.

    Agreement corroborates and raises confidence; a clear conflict is surfaced
    as a warning and the confidence is cut, so the user sees the uncertainty
    instead of a confident wrong number.
    """
    lower = text.lower()
    for key, pattern in TEXT_PATTERNS.items():
        field = plan.get(key)
        if not field or not field.determined:
            continue
        match = re.search(pattern, lower)
        if not match:
            continue
        text_value = float(match.group(1))
        if text_value == 0:
            continue
        drift = abs(field.value - text_value) / text_value
        if drift <= 0.10:
            field.confidence = max(field.confidence, 0.95)
        else:
            field.confidence = min(field.confidence, 0.5)
            msg = (f"{key}: vision read {field.value} but text layer says "
                   f"{text_value}")
            field.note = (field.note + "; " if field.note else "") + msg
            plan.warnings.append(msg)
