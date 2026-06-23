# Compliance Defect Window

A prototype that reads a site-plan PDF, extracts zoning measurements, checks them
against bylaw rules, and shows exactly where the proposal fails — in a results
table and as an annotated PDF.

Built for the PlotPrefect technical assessment.

## What It Does

```
PDF Upload -> Extraction -> Measurement -> Compliance Rules -> Defect Window + Annotated PDF
```

1. Upload a site-plan PDF
2. Extract lot dimensions, building footprint, setbacks, height, and parking
3. Derive areas and lot coverage
4. Check every value against the zoning rules
5. Show a defect window (Rule, Required, Actual, Status) and an annotated PDF
   with failures boxed in red
6. Report a confidence score for each value, and "Unable to determine" when a
   value can't be read reliably

## Architecture

The pipeline runs in three independent stages so each is testable on its own and
the hardest part — reading a drawing — stays swappable.

| Stage | Responsibility | Key modules |
|-------|----------------|-------------|
| Perception | Read raw values from the PDF | `extraction/` |
| Derivation | Compute areas and coverage, carry confidence | `measurement/` |
| Rules | Evaluate values against bylaws | `compliance/` |

Extraction sits behind one interface with two backends:

- **Claude vision** (default) reads the rendered page, handles varied drawing
  styles, and emits confidence and bounding boxes for annotation
- **Local** (offline) reads the embedded text layer with PyMuPDF and pdfplumber,
  needs no API key, and runs fully air-gapped

If `EXTRACTOR=claude` but no API key is present, the app falls back to the local
backend automatically. Both return the same data shape, so nothing downstream
changes. See `docs/architecture.md` for the full diagram and `docs/tech-stack.md`
for the stack choices and trade-offs.

## Tech Stack

- **Backend** Python, FastAPI
- **PDF** PyMuPDF for rendering and annotation, pdfplumber for the text layer
- **Extraction** Claude vision via the Anthropic SDK, with a local fallback
- **Frontend** Next.js, React, TypeScript, Tailwind

## Setup

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env          # add ANTHROPIC_API_KEY to use Claude vision
python sample_data/generate_sample.py   # writes a test site plan

uvicorn app.main:app --reload   # serves on http://127.0.0.1:8000
pytest                          # run the test suite
```

Set `EXTRACTOR=local` in `.env` to run without any API key.

### API

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/analyze` | Upload a PDF, get the defect report + annotated PDF URL |
| GET | `/api/annotated/{id}` | The annotated PDF |
| GET | `/api/source/{id}` | The original upload |
| GET | `/api/health` | Status and the resolved extractor backend |

### Frontend

```bash
cd frontend
npm install
npm run dev          # http://localhost:3000
```

The frontend proxies `/api/*` to the backend (`http://127.0.0.1:8000` by
default, override with `BACKEND_URL`), so start the backend first. Run both and
upload `backend/sample_data/site_plan_sample.pdf` to see the defect window.

## Sample Data

`backend/sample_data/generate_sample.py` builds a synthetic, to-scale site plan
with known values, including deliberate failures so the defect window has
something to show:

| Measurement | Value | Expected |
|-------------|-------|----------|
| Front setback | 5.2 m | FAIL (min 6.0) |
| Rear setback | 8.1 m | PASS (min 7.5) |
| Side setback | 1.3 m | FAIL (min 1.5) |
| Lot coverage | ~41% | PASS (max 45) |
| Building height | 9.5 m | PASS (max 10) |
| Parking | 2 | PASS (min 2) |

## Zoning Rules

Front setback >= 6.0 m, rear setback >= 7.5 m, side setback >= 1.5 m, lot
coverage <= 45%, building height <= 10 m, and parking >= 2 spaces. Rules live in
config (`compliance/rules.py`), so a new bylaw is data, not code.

## Handling Uncertainty

Drawings vary, so the system treats every reading as uncertain and makes that
visible instead of hiding it.

- Each value carries a confidence score, shown as a badge in the UI and a
  percentage in the API
- A value that can't be read is reported as "Unable to determine" with a reason,
  never a guess
- A failed rule and an unreadable value are different states: FAIL means the
  bylaw is broken, UNKNOWN means the value couldn't be extracted
- Derived values inherit the lowest confidence of their inputs, so a computed
  number is never trusted more than the weakest reading behind it
- The Claude backend cross-checks every reading against the PDF text layer:
  agreement raises confidence, a conflict lowers it and raises a warning

## Project Structure

```
backend/   FastAPI service: extraction, measurement, compliance, annotation, API
frontend/  Next.js UI: upload, defect window, annotated viewer, confidence
docs/      Architecture diagram, tech-stack rationale, and demo script
```

## Testing

```bash
cd backend && pytest      # 12 tests: pipeline, annotation, API
cd frontend && npm run build   # type-check + production build
```

The local backend is covered end-to-end on the synthetic sample. The Claude
backend is exercised by adding `ANTHROPIC_API_KEY` to `.env`; without a key the
app runs the local backend so the whole flow still works offline.

## Assumptions

- The PDF is a single-page site plan in metric units
- Where a drawing carries a data block or labelled dimensions, those are the
  authoritative source
- The governing side setback is the smallest of the labelled sides
- Lot coverage is building footprint area divided by lot area


## Build Status

- [x] Phase 1 — Project scaffold and sample-data generator
- [x] Phase 2 — Extraction layer (schema, rendering, Claude + local backends)
- [x] Phase 3 — Measurement and compliance engines (with tests)
- [x] Phase 4 — PDF annotation (red/amber boxes, numbered markers, legend)
- [x] Phase 5 — API (analyze, annotated/source PDF serving, health)
- [x] Phase 6 — Frontend (upload, defect window, annotated viewer, confidence)
- [x] Phase 7 — Docs, tests, and demo polish
