"""Annotate a site-plan PDF with its compliance failures.

Draws a coloured box and a numbered marker on each failing (or undeterminable)
value, and a matching legend in the right margin so labels never cover the
drawing. Boxes come straight from the extraction bounding boxes, so the marks
land where the value was read. Failures without a box still appear in the
legend, flagged as "location not marked", so nothing is silently dropped.
"""
from typing import List

import fitz  # PyMuPDF

from ..compliance.engine import CheckResult, ComplianceReport, Status
from ..extraction.schema import BBox

RED = (0.86, 0.15, 0.15)
AMBER = (0.90, 0.58, 0.10)
GREY = (0.40, 0.40, 0.40)
WHITE = (1, 1, 1)

LEGEND_X = 410       # right-margin column (page is 595 wide)
LEGEND_W = 178
PAD = 3              # padding around a value's box


def annotate(pdf_path: str, report: ComplianceReport, out_path: str) -> str:
    """Write an annotated copy and return its path."""
    doc = fitz.open(pdf_path)
    try:
        flagged = [r for r in report.results
                   if r.status in (Status.FAIL, Status.UNKNOWN)]

        for i, result in enumerate(flagged, start=1):
            color = RED if result.status == Status.FAIL else AMBER
            if result.bbox is not None:
                page = doc[result.bbox.page]
                rect = _denorm(result.bbox, page)
                page.draw_rect(rect, color=color, width=1.8)
                _marker(page, fitz.Point(rect.x0, rect.y0), i, color)

        _legend(doc[0], flagged)
        doc.save(out_path)
        return out_path
    finally:
        doc.close()


def _denorm(bbox: BBox, page: "fitz.Page") -> "fitz.Rect":
    w, h = page.rect.width, page.rect.height
    return fitz.Rect(
        bbox.x0 * w - PAD, bbox.y0 * h - PAD,
        bbox.x1 * w + PAD, bbox.y1 * h + PAD,
    )


def _marker(page: "fitz.Page", at: "fitz.Point", n: int, color) -> None:
    """A small filled disc with a white number, anchored at a box corner."""
    center = fitz.Point(at.x - 2, at.y - 2)
    page.draw_circle(center, 7, color=color, fill=color)
    page.insert_text(
        fitz.Point(center.x - (3 if n < 10 else 6), center.y + 3),
        str(n), fontsize=9, color=WHITE,
    )


def _legend(page: "fitz.Page", flagged: List[CheckResult]) -> None:
    """Stacked callouts in the right margin, numbered to match the markers."""
    x, y = LEGEND_X, 150.0
    title = (f"COMPLIANCE: {sum(r.status == Status.FAIL for r in flagged)} "
             f"failed")
    page.insert_text(fitz.Point(x, y), title, fontsize=11, color=RED)
    y += 8

    if not flagged:
        page.insert_text(fitz.Point(x, y + 14),
                         "No defects found.", fontsize=9, color=GREY)
        return

    for i, r in enumerate(flagged, start=1):
        color = RED if r.status == Status.FAIL else AMBER
        y += 18
        _marker(page, fitz.Point(x + 7, y), i, color)
        lines = _legend_lines(r)
        for j, line in enumerate(lines):
            page.insert_text(
                fitz.Point(x + 16, y + 3 + j * 11),
                line, fontsize=7.5, color=(0.1, 0.1, 0.1),
            )
        y += 11 * (len(lines) - 1)


def _legend_lines(r: CheckResult) -> List[str]:
    head = r.label
    if r.status == Status.FAIL:
        detail = f"{r.actual} (req {r.required})"
        note = r.message or ""
    else:
        detail = "Unable to determine"
        note = "location not marked" if r.bbox is None else ""
    lines = [head, detail]
    if note:
        lines.append(note)
    return _wrap(lines, width=34)


def _pdf_safe(s: str) -> str:
    """Default PDF base fonts lack >= / <= glyphs; use ASCII in annotations."""
    return s.replace("≥", ">=").replace("≤", "<=")


def _wrap(lines: List[str], width: int) -> List[str]:
    out: List[str] = []
    for line in (_pdf_safe(s) for s in lines):
        while len(line) > width:
            cut = line.rfind(" ", 0, width)
            cut = cut if cut > 0 else width
            out.append(line[:cut])
            line = line[cut:].lstrip()
        out.append(line)
    return out
