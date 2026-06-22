"""Claude vision extractor: reads the rendered page and returns structured data.

This is the primary backend. The model reads dimension labels and the drawn
geometry together, so it generalizes across drawing styles and emits its own
confidence and "unable to determine" judgments. The embedded text layer is
passed as grounding and used to cross-check numbers afterwards, which catches
the model's biggest failure mode (a plausible but wrong reading).
"""
import base64
import logging
import re
from typing import Dict, Optional

import anthropic

from . import render
from .local_extractor import PATTERNS as TEXT_PATTERNS
from .schema import (
    FIELD_KEYS,
    FIELD_UNITS,
    BBox,
    Field,
    SitePlan,
    Source,
    undetermined,
)

logger = logging.getLogger(__name__)

TOOL_NAME = "report_site_plan"

SYSTEM = (
    "You are an expert at reading architectural site plans. You extract zoning "
    "measurements precisely and you never invent a value. If a measurement is "
    "not clearly readable, return null for it and say why in its note. Report "
    "all lengths in metres and areas in square metres."
)

INSTRUCTIONS = (
    "Extract the site-plan measurements using the {tool} tool.\n"
    "For each field provide: value (number in metres / square metres, or null "
    "if not determinable), confidence 0..1, an optional short note, and a bbox "
    "tightly around the relevant label or geometry.\n"
    "bbox coordinates are normalized 0..1 with the origin at the TOP-LEFT of "
    "the page (x0,y0 = top-left corner, x1,y1 = bottom-right).\n"
    "side_setback is the governing (smallest) side setback.\n\n"
    "The PDF's embedded text layer is provided below as a hint. Trust the "
    "drawing when it conflicts, but use the text to confirm numbers:\n"
    "-------- TEXT LAYER --------\n{text}\n----------------------------"
)


def _field_schema() -> dict:
    return {
        "type": "object",
        "properties": {
            "value": {"type": ["number", "null"]},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "note": {"type": ["string", "null"]},
            "bbox": {
                "type": ["object", "null"],
                "properties": {
                    "x0": {"type": "number"},
                    "y0": {"type": "number"},
                    "x1": {"type": "number"},
                    "y1": {"type": "number"},
                },
                "required": ["x0", "y0", "x1", "y1"],
            },
        },
        "required": ["value", "confidence"],
    }


def _tool() -> dict:
    return {
        "name": TOOL_NAME,
        "description": "Report every extracted site-plan measurement.",
        "input_schema": {
            "type": "object",
            "properties": {k: _field_schema() for k in FIELD_KEYS},
            "required": FIELD_KEYS,
        },
    }


# OAuth tokens (sk-ant-oat..., from `claude setup-token`) authenticate over
# Authorization: Bearer and need this beta header; Console API keys
# (sk-ant-api...) use x-api-key and ignore it.
OAUTH_BETA_HEADER = "oauth-2025-04-20"


class VisionExtractor:
    name = "claude"

    def __init__(self, model: str, api_key: Optional[str] = None,
                 auth_token: Optional[str] = None):
        if api_key:
            self.client = anthropic.Anthropic(api_key=api_key)
        elif auth_token:
            self.client = anthropic.Anthropic(
                auth_token=auth_token,
                default_headers={"anthropic-beta": OAUTH_BETA_HEADER},
            )
        else:
            raise ValueError("VisionExtractor needs an API key or auth token")
        self.model = model

    def extract(self, pdf_path: str) -> SitePlan:
        png = render.render_page_png(pdf_path, page=0, dpi=150)
        text = render.extract_text(pdf_path)
        width_pt, height_pt = render.page_dimensions(pdf_path)

        plan = SitePlan(
            backend=self.name,
            source_pdf=pdf_path,
            page_count=render.page_count(pdf_path),
            page_width_pt=width_pt,
            page_height_pt=height_pt,
        )

        raw = self._call_model(png, text)
        for key in FIELD_KEYS:
            plan.set(self._to_field(key, raw.get(key)))

        self._cross_check(plan, text)
        return plan

    def _call_model(self, png: bytes, text: str) -> Dict[str, dict]:
        b64 = base64.standard_b64encode(png).decode("ascii")
        # Forced tool_choice guarantees a single structured response. It is
        # intentionally paired with no `thinking` param: forcing a specific
        # tool is incompatible with extended/adaptive thinking, and a one-shot
        # extraction does not need it. max_tokens has generous headroom so the
        # tool-input JSON is never truncated.
        message = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=SYSTEM,
            tools=[_tool()],
            tool_choice={"type": "tool", "name": TOOL_NAME},
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {
                        "type": "base64", "media_type": "image/png",
                        "data": b64}},
                    {"type": "text", "text": INSTRUCTIONS.format(
                        tool=TOOL_NAME, text=text or "(no text layer)")},
                ],
            }],
        )
        for block in message.content:
            if block.type == "tool_use" and block.name == TOOL_NAME:
                return block.input
        raise RuntimeError("Vision model returned no structured output")

    def _to_field(self, key: str, data: Optional[dict]) -> Field:
        if not data or data.get("value") is None:
            note = (data or {}).get("note") or "Unable to determine"
            return undetermined(key, note)
        bbox = None
        b = data.get("bbox")
        if b and all(k in b for k in ("x0", "y0", "x1", "y1")):
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

    def _cross_check(self, plan: SitePlan, text: str) -> None:
        """Reconcile vision readings with the embedded text layer.

        Agreement corroborates and raises confidence; a clear conflict is
        surfaced as a warning and the confidence is cut, so the user sees the
        uncertainty instead of a confident wrong number.
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
