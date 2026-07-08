"""OpenAI vision extractor: reads the rendered page and returns structured data.

The primary backend. It renders the page to PNG, sends it to a vision model with
a forced function call for structured output, maps the result into the shared
SitePlan shape, and cross-checks every reading against the PDF text layer.
Because it returns the same SitePlan, it drops in behind the Extractor interface
with no downstream changes.
"""
import base64
import json
import logging
from typing import Dict

from openai import OpenAI

from . import render
from .common import cross_check, to_field
from .schema import FIELD_KEYS, SitePlan

logger = logging.getLogger(__name__)

FUNCTION_NAME = "report_site_plan"

SYSTEM = (
    "You are an expert at reading architectural site plans. You extract zoning "
    "measurements precisely and you never invent a value. If a measurement is "
    "not clearly readable, return null for it and say why in its note. Report "
    "all lengths in metres and areas in square metres."
)

INSTRUCTIONS = (
    "Extract the site-plan measurements using the {func} function.\n"
    "For each field provide: value (number in metres / square metres, or null "
    "if not determinable), confidence 0..1, a short note (or null), and a bbox "
    "tightly around the relevant label or geometry (or null).\n"
    "bbox coordinates are normalized 0..1 with the origin at the TOP-LEFT of "
    "the page (x0,y0 = top-left corner, x1,y1 = bottom-right).\n"
    "side_setback is the governing (smallest) side setback.\n\n"
    "The PDF's embedded text layer is provided below as a hint. Trust the "
    "drawing when it conflicts, but use the text to confirm numbers:\n"
    "-------- TEXT LAYER --------\n{text}\n----------------------------"
)


def _field_schema() -> dict:
    # Strict structured outputs accept only a subset of JSON Schema: every
    # property must be listed in `required` and `additionalProperties` must be
    # false. Nullability is expressed with a "null" type, not by omission, and
    # numeric bounds (minimum/maximum) are not allowed here.
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "value": {"type": ["number", "null"]},
            "confidence": {"type": "number"},
            "note": {"type": ["string", "null"]},
            "bbox": {
                "type": ["object", "null"],
                "additionalProperties": False,
                "properties": {
                    "x0": {"type": "number"},
                    "y0": {"type": "number"},
                    "x1": {"type": "number"},
                    "y1": {"type": "number"},
                },
                "required": ["x0", "y0", "x1", "y1"],
            },
        },
        "required": ["value", "confidence", "note", "bbox"],
    }


def _parameters_schema() -> dict:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {k: _field_schema() for k in FIELD_KEYS},
        "required": FIELD_KEYS,
    }


class OpenAIExtractor:
    name = "openai"

    def __init__(self, model: str, api_key: str):
        if not api_key:
            raise ValueError("OpenAIExtractor needs an API key")
        self.client = OpenAI(api_key=api_key)
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
            plan.set(to_field(key, raw.get(key)))

        cross_check(plan, text)
        return plan

    def _call_model(self, png: bytes, text: str) -> Dict[str, dict]:
        b64 = base64.standard_b64encode(png).decode("ascii")
        # A forced function call guarantees a single structured response.
        # strict=True binds the arguments to the schema so the tool JSON is
        # never malformed.
        response = self.client.chat.completions.create(
            model=self.model,
            max_completion_tokens=4096,
            messages=[
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": [
                    {"type": "text", "text": INSTRUCTIONS.format(
                        func=FUNCTION_NAME, text=text or "(no text layer)")},
                    {"type": "image_url", "image_url": {
                        "url": f"data:image/png;base64,{b64}"}},
                ]},
            ],
            tools=[{
                "type": "function",
                "function": {
                    "name": FUNCTION_NAME,
                    "description": "Report every extracted site-plan measurement.",
                    "parameters": _parameters_schema(),
                    "strict": True,
                },
            }],
            tool_choice={"type": "function",
                         "function": {"name": FUNCTION_NAME}},
        )
        for call in (response.choices[0].message.tool_calls or []):
            if call.function.name == FUNCTION_NAME:
                return json.loads(call.function.arguments)
        raise RuntimeError("Vision model returned no structured output")
