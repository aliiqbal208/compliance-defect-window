# Technology Choices

This document records the stack behind the Compliance Defect Window and the
reasoning for each choice. The brief rewards architecture decisions, handling
uncertainty, and justified trade-offs over raw feature count, so every choice
below is measured against those goals and the 72-hour scope.

## At a Glance

| Layer | Choice | Primary reason |
|-------|--------|----------------|
| Backend | Python, FastAPI | Strongest PDF and AI ecosystem; typed, low-boilerplate API |
| PDF render and annotate | PyMuPDF | Rasterizes pages and draws overlays in one library |
| Text extraction | pdfplumber | Exact text layer plus word bounding boxes |
| Extraction model | Claude vision, with a local fallback | Generalizes across drawings; confidence and boxes for free |
| Data modeling | Pydantic | One typed contract shared by the pipeline and the API |
| Frontend | Next.js, React, TypeScript, Tailwind | Single-page UI, built-in API proxy, type parity with the backend |
| PDF viewer | Native browser iframe | Renders the annotated PDF with zero extra dependencies |
| Tests | pytest | Fast, deterministic, offline |

## Decision Principles

Three principles drove the choices:

- Keep the messy part — reading a drawing — isolated and swappable
- Make uncertainty a first-class output, not an afterthought
- Favor a cohesive single-language pipeline over breadth that the timebox can't support

## Backend Language and Framework — Python and FastAPI

Python wins on ecosystem: PyMuPDF, pdfplumber, and the Anthropic SDK all live
here, so the entire pipeline stays in one language with no glue layer. FastAPI
adds typed request and response models through Pydantic, async file uploads,
and automatic validation with very little boilerplate.

The alternative was a Node backend. That would push the PDF and vision work into
a weaker library ecosystem or split the system across two languages. A single
Python service keeps extraction, measurement, rules, and annotation cohesive.

## PDF Handling — PyMuPDF and pdfplumber

These two libraries are complementary, and each is best at its own job:

- PyMuPDF rasterizes a page to PNG for the vision model and draws the boxes,
  markers, and labels onto the annotated output
- pdfplumber reads the embedded text layer exactly and returns per-word bounding
  boxes, which is ideal for finding labelled values and locating them for
  annotation

Using both avoids stretching one tool past its strength. pdfminer alone is
lower-level and slower, and it doesn't render or draw; PyMuPDF covers the pixel
and drawing side that pdfminer can't.

## Extraction — Claude Vision, with an Offline Fallback

Extraction is the hard part, and it's where the architecture earns its keep.
Site plans vary widely, so a vision model is the primary backend: it generalizes
across drawing styles, emits a confidence score per value, says "unable to
determine" instead of guessing, and returns bounding boxes that drive the
annotation — all in a single call. The model is Claude Opus 4.8 through the
Anthropic SDK.

A rule-based computer-vision approach (line detection plus OCR) was considered
and rejected for the MVP. It's brittle across real drawings and would consume
the whole timebox for a worse result.

A second backend reads the text layer with pdfplumber and regex. It needs no API
key and runs fully offline. Both backends return the same data shape behind one
interface, so the rest of the system never knows which one ran. That gives the
prototype three things at once: no vendor lock-in, an air-gapped mode, and a
clean place to swap perception strategies later.

## Data Modeling — Pydantic

Pydantic defines the typed contracts — SitePlan, Field, and CheckResult — that
flow between stages, and FastAPI reuses the same models as request and response
schemas. Validation happens at the boundaries, so a malformed value fails early
and visibly rather than deep in the pipeline.

## Frontend — Next.js, React, TypeScript, and Tailwind

This matches the stack the brief lists, and each part pulls its weight. Next.js
gives a clean single-page app and a dev-server rewrite that proxies every
`/api/*` call to FastAPI, which removes CORS from the picture entirely.
TypeScript mirrors the backend models, so the contract is enforced on both
sides. Tailwind keeps styling fast and consistent without a separate CSS system.

The trade-off is that Next.js is heavier than a plain SPA, but the built-in
proxy and conventions are worth more than the weight at this scope.

## PDF Viewing — Native Browser Iframe

The annotated PDF renders in a native `iframe`, so there's no PDF rendering
dependency in the frontend. PDF.js would add significant weight for no benefit,
since the browser already renders PDFs well.

## Testing — pytest

pytest keeps tests fast and low-ceremony, covering the pipeline, annotation, and
API surface. A synthetic site-plan PDF with known values is the fixture, so the
suite is deterministic and runs offline regardless of any configured credential.

## What Got Rejected and Why

- Rule-based CV extraction (OpenCV line detection plus OCR) — brittle across
  drawing styles and a poor use of the timebox
- Tesseract OCR in the MVP — adds a native binary for the scanned-PDF path the
  demo never exercises; kept as future work
- A separate Node backend — would fragment the PDF and vision work or duplicate
  logic across two languages
- A PDF.js viewer — unnecessary weight when an iframe renders the result
