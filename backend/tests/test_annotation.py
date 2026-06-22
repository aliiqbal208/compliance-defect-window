"""Annotation produces a valid PDF and survives the awkward cases."""
import fitz

from app.annotation.annotator import annotate
from app.compliance.engine import evaluate
from app.extraction.local_extractor import LocalExtractor
from app.extraction.schema import SitePlan
from app.measurement.engine import derive


def test_annotation_writes_valid_pdf(sample_pdf, tmp_path):
    report = evaluate(derive(LocalExtractor().extract(sample_pdf)))
    out = str(tmp_path / "annotated.pdf")
    annotate(sample_pdf, report, out)

    doc = fitz.open(out)
    assert doc.page_count == 1
    # the drawing now carries vector annotations (boxes, markers, legend)
    assert len(doc[0].get_drawings()) > 0


def test_annotation_handles_all_unknown(sample_pdf, tmp_path):
    # an empty plan -> every rule UNKNOWN, no boxes, legend still renders
    report = evaluate(SitePlan())
    out = str(tmp_path / "unknown.pdf")
    annotate(sample_pdf, report, out)
    assert fitz.open(out).page_count == 1
