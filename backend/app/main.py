"""FastAPI app: upload a site plan, get back a defect report + annotated PDF."""
import logging
import uuid
from pathlib import Path
from typing import Dict, List

import fitz  # PyMuPDF
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .annotation.annotator import annotate
from .compliance.engine import CheckResult
from .config import get_settings
from .extraction.schema import Field
from .pipeline import analyze

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Compliance Defect Window", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

SOURCE_NAME = "source.pdf"
ANNOTATED_NAME = "annotated.pdf"


class Summary(BaseModel):
    passed: int
    failed: int
    unknown: int


class AnalyzeResponse(BaseModel):
    id: str
    backend: str
    source_filename: str
    compliant: bool
    summary: Summary
    checks: List[CheckResult]
    fields: Dict[str, Field]
    warnings: List[str]
    annotated_pdf_url: str


def _job_dir(job_id: str) -> Path:
    return get_settings().storage_path / job_id


def _is_pdf(path: Path) -> bool:
    try:
        with fitz.open(path) as doc:
            return doc.page_count > 0
    except Exception:  # noqa: BLE001
        return False


@app.get("/api/health")
def health() -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "extractor_requested": settings.extractor,
        "extractor_resolved": settings.resolved_extractor,
    }


@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze_endpoint(file: UploadFile = File(...)) -> AnalyzeResponse:
    if file.content_type not in ("application/pdf", "application/octet-stream") \
            and not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(400, "Please upload a PDF file.")

    job_id = uuid.uuid4().hex
    job_dir = _job_dir(job_id)
    job_dir.mkdir(parents=True, exist_ok=True)
    source = job_dir / SOURCE_NAME
    source.write_bytes(await file.read())

    if not _is_pdf(source):
        raise HTTPException(400, "The uploaded file is not a readable PDF.")

    plan, report = analyze(str(source))
    annotate(str(source), report, str(job_dir / ANNOTATED_NAME))

    return AnalyzeResponse(
        id=job_id,
        backend=plan.backend,
        source_filename=file.filename or SOURCE_NAME,
        compliant=report.compliant,
        summary=Summary(passed=report.passed, failed=report.failed,
                        unknown=report.unknown),
        checks=report.results,
        fields=plan.fields,
        warnings=plan.warnings,
        annotated_pdf_url=f"/api/annotated/{job_id}",
    )


@app.get("/api/annotated/{job_id}")
def annotated(job_id: str) -> FileResponse:
    return _serve(job_id, ANNOTATED_NAME, "annotated.pdf")


@app.get("/api/source/{job_id}")
def source(job_id: str) -> FileResponse:
    return _serve(job_id, SOURCE_NAME, "source.pdf")


def _serve(job_id: str, name: str, download_name: str) -> FileResponse:
    path = _job_dir(job_id) / name
    if not path.exists():
        raise HTTPException(404, "Not found.")
    return FileResponse(path, media_type="application/pdf",
                        filename=download_name)
