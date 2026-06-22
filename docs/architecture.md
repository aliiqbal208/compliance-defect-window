# Architecture

## Flow

```
              ┌──────────────┐
              │  PDF Upload  │
              └──────┬───────┘
                     ▼
         ┌───────────────────────┐
         │   Extraction Layer    │   Claude vision  OR  local (offline)
         │  (swappable backend)  │   -> SitePlan { fields, confidence, bbox }
         └───────────┬───────────┘
                     ▼
         ┌───────────────────────┐
         │   Measurement Engine  │   derive lot area, footprint area,
         │                       │   lot coverage; propagate confidence
         └───────────┬───────────┘
                     ▼
         ┌───────────────────────┐
         │  Compliance Rules     │   evaluate each value vs bylaw
         │  Engine (config)      │   -> Defect { required, actual, status }
         └─────┬───────────┬─────┘
               ▼           ▼
     ┌──────────────┐  ┌──────────────────┐
     │ Defect Window│  │  Annotated PDF   │
     │   (table)    │  │ (red boxes/labels)│
     └──────────────┘  └──────────────────┘
```

## Why This Shape

The assessment rewards how the problem is structured, how ambiguity is handled,
and how trade-offs are justified. Three decisions follow from that.

### 1. Three Independent Stages

Perception, derivation, and rules are separate. Extraction is the only stage
that deals with uncertainty. Measurement is pure arithmetic. Rules are pure
comparison. Splitting them keeps each one small, testable, and replaceable, and
it isolates the messy part (reading a drawing) from the parts that must be
exact.

### 2. Extraction Is an Interface, Not a Vendor

`Extractor` is a protocol with two backends behind it:

- **Claude vision** reads the rendered page image. It generalizes across drawing
  styles, produces a confidence score per value, says "unable to determine"
  instead of guessing, and returns bounding boxes that drive annotation.
- **Local** reads the embedded text layer with pdfplumber and locates values
  with PyMuPDF. It needs no API key and runs fully offline.

A vision model is the primary backend because hand-built line detection and OCR
parsing are brittle across real drawings and would cost far more to build for a
worse result. The risk is a confident wrong reading, so the vision backend
cross-checks every number against the text layer: agreement raises confidence, a
clear conflict cuts it and surfaces a warning.

The local backend exists so a client with no Claude access can still run the
whole pipeline. The contract is identical, so the rest of the system never knows
which backend ran. Confidence and "unable to determine" carry the difference in
reliability to the user.

### 3. Uncertainty Is a First-Class Output

Every `Field` carries `value`, `confidence`, a `source`, an optional `bbox`, and
a `note`. A value that can't be read is `value = None` with a note, never a
substituted guess. Confidence propagates through derivation as the minimum of
its inputs, so a derived value is never more trusted than the weakest number it
came from.

## Data Shape

```
SitePlan
  fields: { name -> Field }
  backend, source_pdf, page_count, page_width_pt, page_height_pt, warnings[]

Field
  name, value (nullable), unit, confidence (0..1),
  source (vision | text | derived), bbox (nullable), note
```

Bounding boxes are normalized 0..1 with a top-left origin, so they are
resolution-independent and map cleanly onto PDF points at annotation time.

## Module Map

```
backend/app/
  config.py              settings + backend selection rules
  extraction/
    schema.py            SitePlan, Field, BBox (the shared contract)
    render.py            rasterize, text layer, positioned words
    base.py              Extractor protocol + factory with fallback
    vision_extractor.py  Claude vision backend
    local_extractor.py   offline text-layer backend
  measurement/engine.py  derive lot area + lot coverage, propagate confidence
  compliance/
    rules.py             zoning rules as configuration
    engine.py            evaluate values -> CheckResult (PASS / FAIL / UNKNOWN)
  annotation/annotator.py  draw boxes, markers, legend onto a PDF copy
  pipeline.py            orchestrate extract -> measure -> evaluate (+ fallback)
  main.py                FastAPI app (analyze, annotated/source, health)
tests/                   pipeline, annotation, and API tests
```
