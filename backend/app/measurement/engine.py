"""Measurement engine: derive values the drawing implies but doesn't state.

Pure arithmetic on top of extraction. Derived values are added to the same
SitePlan with source=DERIVED. Confidence propagates as the minimum of the inputs
a value is built from, so a derived number is never trusted more than the
weakest reading behind it. A value that can't be derived stays "Unable to
determine".
"""
from typing import List, Optional

from ..extraction.schema import Field, SitePlan, Source, undetermined

CONSISTENCY_TOLERANCE = 0.10  # 10% mismatch between stated and computed area


def derive(plan: SitePlan) -> SitePlan:
    """Add lot area and footprint area (if implied), and lot coverage."""
    _ensure_lot_area(plan)
    _ensure_footprint_area(plan)
    _lot_coverage(plan)
    return plan


def _ensure_footprint_area(plan: SitePlan) -> None:
    """Compute footprint area from its width x depth when not stated, and flag a
    stated area that disagrees with the dimensions."""
    area = plan.get("building_footprint_area")
    width = plan.get("building_footprint_width")
    depth = plan.get("building_footprint_depth")

    computed = None
    if width and width.determined and depth and depth.determined:
        computed = width.value * depth.value

    if area and area.determined:
        if computed is not None and area.value:
            drift = abs(area.value - computed) / area.value
            if drift > CONSISTENCY_TOLERANCE:
                msg = (f"building_footprint_area stated {area.value:g} but "
                       f"width x depth = {computed:g}")
                area.note = (area.note + "; " if area.note else "") + msg
                area.confidence = min(area.confidence, 0.5)
                plan.warnings.append(msg)
        return

    if computed is not None:
        plan.set(Field(
            name="building_footprint_area",
            value=round(computed, 2),
            unit="sq m",
            confidence=_min_conf([width, depth]),
            source=Source.DERIVED,
            note="derived from footprint width x depth",
        ))


def _ensure_lot_area(plan: SitePlan) -> None:
    """Compute lot area from width x depth when it isn't stated, and flag a
    stated area that disagrees with the dimensions."""
    area = plan.get("lot_area")
    width = plan.get("lot_width")
    depth = plan.get("lot_depth")

    computed = None
    if width and width.determined and depth and depth.determined:
        computed = width.value * depth.value

    if area and area.determined:
        if computed is not None and area.value:
            drift = abs(area.value - computed) / area.value
            if drift > CONSISTENCY_TOLERANCE:
                msg = (f"lot_area stated {area.value:g} but width x depth = "
                       f"{computed:g}")
                area.note = (area.note + "; " if area.note else "") + msg
                area.confidence = min(area.confidence, 0.5)
                plan.warnings.append(msg)
        return

    if computed is not None:
        plan.set(Field(
            name="lot_area",
            value=round(computed, 2),
            unit="sq m",
            confidence=_min_conf([width, depth]),
            source=Source.DERIVED,
            note="derived from lot width x depth",
        ))
    else:
        plan.set(undetermined("lot_area"))


def _lot_coverage(plan: SitePlan) -> None:
    """Lot coverage = footprint area / lot area, as a percentage."""
    footprint = plan.get("building_footprint_area")
    lot_area = plan.get("lot_area")

    if not (footprint and footprint.determined
            and lot_area and lot_area.determined and lot_area.value):
        plan.set(undetermined(
            "lot_coverage",
            "needs building footprint and lot area",
        ))
        return

    coverage = footprint.value / lot_area.value * 100
    plan.set(Field(
        name="lot_coverage",
        value=round(coverage, 1),
        unit="%",
        confidence=_min_conf([footprint, lot_area]),
        source=Source.DERIVED,
        bbox=footprint.bbox,  # point annotation at the footprint
        note="derived from footprint / lot area",
    ))


def _min_conf(fields: List[Optional[Field]]) -> float:
    confidences = [f.confidence for f in fields if f and f.determined]
    return min(confidences) if confidences else 0.0
