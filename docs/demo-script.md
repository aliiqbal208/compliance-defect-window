# Demo Script (5 minutes)

A suggested running order for the video. The assessment asks to show PDF upload,
the compliance defect window, and the annotated drawing.

## 0:00 - Setup (10s)

Two terminals running:

```bash
# terminal 1
cd backend && source .venv/bin/activate && uvicorn app.main:app --reload
# terminal 2
cd frontend && npm run dev
```

Open http://localhost:3000.

## 0:10 - The Problem (30s)

One line on what this solves: applicants need to catch zoning defects before they
submit. Show the empty upload screen.

## 0:40 - Upload (30s)

Drag in `backend/sample_data/site_plan_sample.pdf`. Mention it's a synthetic plan
with known values, including deliberate failures.

## 1:10 - Defect Window (90s)

Walk the results table:

- Front Setback 5.2 m, required >= 6.0 m, FAIL, deficient by 0.8 m
- Side Setback 1.3 m, required >= 1.5 m, FAIL, deficient by 0.2 m
- Rear, Lot Coverage, Height, Parking all PASS

Point out the confidence badges and the pass / fail / unknown summary.

## 2:40 - Annotated Drawing (60s)

Switch to the annotated PDF panel. Show the red boxes and numbered markers on the
two failing values, and the legend that ties each marker to its defect.

## 3:40 - Handling Uncertainty (50s)

Explain the design point reviewers care about:

- Confidence per value, "Unable to determine" instead of guessing
- FAIL vs UNKNOWN are distinct states
- Two extractor backends behind one interface: Claude vision and a fully offline
  local backend, with automatic fallback

## 4:30 - Architecture (30s)

Show the diagram in `docs/architecture.md`: upload, extraction, measurement,
rules, defect window, annotated PDF. Close on the three-stage separation and why
extraction is swappable.
