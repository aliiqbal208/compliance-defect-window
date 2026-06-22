"""API surface: health, analyze, serving the annotated PDF, bad input."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert "extractor_resolved" in body


def test_analyze_returns_defect_report(sample_pdf):
    with open(sample_pdf, "rb") as f:
        r = client.post("/api/analyze",
                        files={"file": ("plan.pdf", f, "application/pdf")})
    assert r.status_code == 200
    d = r.json()
    assert d["summary"] == {"passed": 4, "failed": 2, "unknown": 0}
    assert d["compliant"] is False
    assert len(d["checks"]) == 6
    assert d["annotated_pdf_url"].endswith(d["id"])

    pdf = client.get(d["annotated_pdf_url"])
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"


def test_rejects_non_pdf():
    r = client.post("/api/analyze",
                    files={"file": ("x.txt", b"hello", "text/plain")})
    assert r.status_code == 400


def test_annotated_404_for_unknown_id():
    assert client.get("/api/annotated/does-not-exist").status_code == 404
