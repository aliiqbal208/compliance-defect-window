"""Generate a synthetic site-plan PDF with known ground-truth values.

This is a *digital* PDF: it carries a real text layer (so pdfplumber reads it
exactly) and to-scale vector geometry (so a vision model can reason spatially).

Ground truth is defined once below and drawn to scale, so the same numbers feed
both the drawing and the README. Values are chosen to mirror the assessment's
example defect window:

    Front Setback  5.2 m   FAIL (>= 6.0)
    Rear Setback   8.1 m   PASS (>= 7.5)
    Side Setback   1.3 m   FAIL (>= 1.5)
    Lot Coverage   ~41%    PASS (<= 45)
    Parking        2       PASS (>= 2)
    Height         9.5 m   PASS (<= 10)

Run:  python sample_data/generate_sample.py [output.pdf]
"""
import sys
from pathlib import Path

import fitz  # PyMuPDF

# --- Ground truth (metres) -------------------------------------------------
LOT_WIDTH = 18.0
LOT_DEPTH = 30.0
FRONT_SETBACK = 5.2   # FAIL (min 6.0)
REAR_SETBACK = 8.1    # PASS (min 7.5)
SIDE_SETBACK_LEFT = 1.3   # FAIL (min 1.5)
BUILDING_WIDTH = 13.2
BUILDING_HEIGHT = 9.5     # PASS (max 10)
PARKING_STALLS = 2

LOT_AREA = LOT_WIDTH * LOT_DEPTH                       # 540.0
BUILDING_DEPTH = LOT_DEPTH - FRONT_SETBACK - REAR_SETBACK  # 16.7
FOOTPRINT_AREA = BUILDING_WIDTH * BUILDING_DEPTH       # ~220.4
SIDE_SETBACK_RIGHT = LOT_WIDTH - SIDE_SETBACK_LEFT - BUILDING_WIDTH  # 3.5
LOT_COVERAGE = FOOTPRINT_AREA / LOT_AREA * 100         # ~40.8%

# --- Drawing layout --------------------------------------------------------
SCALE = 12.0          # points per metre
ORIGIN_X = 190.0      # lot top-left on the page (points)
ORIGIN_Y = 210.0

BLACK = (0, 0, 0)
GREY = (0.45, 0.45, 0.45)
BLUE = (0.1, 0.25, 0.6)


def m(value: float) -> float:
    """Metres -> points."""
    return value * SCALE


def build(out_path: Path) -> None:
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)  # A4 portrait

    # Lot boundary
    lot = fitz.Rect(ORIGIN_X, ORIGIN_Y,
                    ORIGIN_X + m(LOT_WIDTH), ORIGIN_Y + m(LOT_DEPTH))
    page.draw_rect(lot, color=BLACK, width=1.5)

    # Building footprint, placed by setbacks
    bx0 = ORIGIN_X + m(SIDE_SETBACK_LEFT)
    by0 = ORIGIN_Y + m(FRONT_SETBACK)
    building = fitz.Rect(bx0, by0,
                         bx0 + m(BUILDING_WIDTH), by0 + m(BUILDING_DEPTH))
    page.draw_rect(building, color=BLUE, width=1.2, fill=(0.88, 0.91, 0.97))

    # Parking stalls in the front yard (two 2.5 m x 5.0 m bays)
    stall_w, stall_d = m(2.5), m(5.0)
    py = ORIGIN_Y + 2
    for i in range(PARKING_STALLS):
        sx = ORIGIN_X + m(0.8) + i * (stall_w + 4)
        stall = fitz.Rect(sx, py, sx + stall_w, py + stall_d)
        page.draw_rect(stall, color=GREY, width=0.8, dashes="[3] 0")
        page.insert_text((sx + 8, py + stall_d / 2), f"P{i + 1}",
                         fontsize=8, color=GREY)

    # --- Text labels (the text layer pdfplumber reads) ---------------------
    def text(pos, s, size=9, color=BLACK, rotate=0):
        page.insert_text(pos, s, fontsize=size, color=color, rotate=rotate)

    # Title block
    text((ORIGIN_X, 60), "SITE PLAN - PROPOSED SINGLE DWELLING", size=14)
    text((ORIGIN_X, 78), "123 Example Street   |   Scale 1:100 (approx)",
         size=9, color=GREY)

    # Lot dimensions
    text((ORIGIN_X + m(LOT_WIDTH) / 2 - 35, ORIGIN_Y - 8),
         f"Lot Width: {LOT_WIDTH:.1f} m")
    text((ORIGIN_X - 12, ORIGIN_Y + m(LOT_DEPTH) / 2 + 40),
         f"Lot Depth: {LOT_DEPTH:.1f} m", rotate=90)
    text((ORIGIN_X, ORIGIN_Y + m(LOT_DEPTH) + 18),
         f"Lot Area: {LOT_AREA:.0f} sq m")

    # Setback callouts
    text((building.x0 + 6, ORIGIN_Y + m(FRONT_SETBACK) / 2 + 60),
         f"Front Setback: {FRONT_SETBACK:.1f} m", color=BLUE)
    text((building.x0 + 6, building.y1 + m(REAR_SETBACK) / 2),
         f"Rear Setback: {REAR_SETBACK:.1f} m", color=BLUE)
    text((ORIGIN_X + 2, building.y0 + m(BUILDING_DEPTH) / 2),
         f"Side Setback: {SIDE_SETBACK_LEFT:.1f} m", size=8,
         color=BLUE, rotate=90)
    text((building.x1 + 2, building.y0 + m(BUILDING_DEPTH) / 2 + 40),
         f"Side Setback: {SIDE_SETBACK_RIGHT:.1f} m", size=8,
         color=BLUE, rotate=90)

    # Building labels
    text((building.x0 + 18, building.y0 + m(BUILDING_DEPTH) / 2 - 8),
         "PROPOSED DWELLING", size=10)
    text((building.x0 + 18, building.y0 + m(BUILDING_DEPTH) / 2 + 8),
         f"Footprint: {BUILDING_WIDTH:.1f} m x {BUILDING_DEPTH:.1f} m", size=8)
    text((building.x0 + 18, building.y0 + m(BUILDING_DEPTH) / 2 + 22),
         f"Building Height: {BUILDING_HEIGHT:.1f} m", size=8)

    # Parking summary
    text((ORIGIN_X, ORIGIN_Y + m(LOT_DEPTH) + 34),
         f"Parking Stalls: {PARKING_STALLS}")

    # --- Site data table (horizontal text; reliable for both backends) -----
    # Real plans carry a zoning/data block. The rotated callouts above stay for
    # visual realism, but this table is the authoritative, cleanly extractable
    # source of every value.
    tx, ty = ORIGIN_X, ORIGIN_Y + m(LOT_DEPTH) + 64
    text((tx, ty), "SITE DATA", size=11)
    rows = [
        f"Lot Width: {LOT_WIDTH:.1f} m",
        f"Lot Depth: {LOT_DEPTH:.1f} m",
        f"Lot Area: {LOT_AREA:.0f} sq m",
        f"Footprint Width: {BUILDING_WIDTH:.1f} m",
        f"Footprint Depth: {BUILDING_DEPTH:.1f} m",
        f"Building Footprint: {FOOTPRINT_AREA:.1f} sq m",
        f"Front Setback: {FRONT_SETBACK:.1f} m",
        f"Rear Setback: {REAR_SETBACK:.1f} m",
        f"Side Setback: {SIDE_SETBACK_LEFT:.1f} m",
        f"Building Height: {BUILDING_HEIGHT:.1f} m",
        f"Parking Stalls: {PARKING_STALLS}",
    ]
    for i, row in enumerate(rows):
        text((tx, ty + 18 + i * 14), row, size=9)

    doc.save(out_path)
    doc.close()

    print(f"Wrote {out_path}")
    print(f"  Lot {LOT_WIDTH} x {LOT_DEPTH} m  area {LOT_AREA:.0f} sq m")
    print(f"  Footprint {BUILDING_WIDTH} x {BUILDING_DEPTH:.1f} m "
          f"= {FOOTPRINT_AREA:.1f} sq m")
    print(f"  Coverage {LOT_COVERAGE:.1f}%  "
          f"side(right) {SIDE_SETBACK_RIGHT:.1f} m")


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else \
        Path(__file__).parent / "site_plan_sample.pdf"
    build(out)
