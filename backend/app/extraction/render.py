"""PDF rendering and text-layer access — shared by both extractor backends."""
from dataclasses import dataclass
from typing import List, Tuple

import fitz  # PyMuPDF
import pdfplumber


@dataclass
class Word:
    """A positioned token from the text layer (points, top-left origin)."""
    text: str
    x0: float
    top: float
    x1: float
    bottom: float
    page: int


def render_page_png(pdf_path: str, page: int = 0, dpi: int = 150) -> bytes:
    """Rasterize a page to PNG bytes (input for vision extraction)."""
    doc = fitz.open(pdf_path)
    try:
        pix = doc[page].get_pixmap(dpi=dpi)
        return pix.tobytes("png")
    finally:
        doc.close()


def page_dimensions(pdf_path: str, page: int = 0) -> Tuple[float, float]:
    """Page size in points (width, height)."""
    doc = fitz.open(pdf_path)
    try:
        rect = doc[page].rect
        return rect.width, rect.height
    finally:
        doc.close()


def page_count(pdf_path: str) -> int:
    doc = fitz.open(pdf_path)
    try:
        return doc.page_count
    finally:
        doc.close()


def extract_text(pdf_path: str) -> str:
    """Embedded text layer across all pages (exact characters, not OCR)."""
    out: List[str] = []
    with pdfplumber.open(pdf_path) as pdf:
        for p in pdf.pages:
            out.append(p.extract_text() or "")
    return "\n".join(out)


def extract_words(pdf_path: str, page: int = 0) -> List[Word]:
    """Positioned tokens, used to locate values for annotation in local mode."""
    words: List[Word] = []
    with pdfplumber.open(pdf_path) as pdf:
        p = pdf.pages[page]
        for w in p.extract_words():
            words.append(Word(
                text=w["text"], x0=w["x0"], top=w["top"],
                x1=w["x1"], bottom=w["bottom"], page=page,
            ))
    return words
