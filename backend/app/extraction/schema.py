"""Canonical data shapes for extraction.

Every extractor backend (Claude vision, local) returns the *same* SitePlan, so
nothing downstream knows or cares which backend ran. A value that cannot be read
is represented explicitly: value=None with a note, never a guess.
"""
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field as PydField

# The measurements the pipeline understands. Both backends populate this set.
FIELD_KEYS = [
    "lot_width",
    "lot_depth",
    "lot_area",
    "building_footprint_width",
    "building_footprint_depth",
    "building_footprint_area",
    "building_height",
    "front_setback",
    "rear_setback",
    "side_setback",
    "parking_stalls",
]

FIELD_UNITS = {
    "lot_width": "m",
    "lot_depth": "m",
    "lot_area": "sq m",
    "building_footprint_width": "m",
    "building_footprint_depth": "m",
    "building_footprint_area": "sq m",
    "building_height": "m",
    "front_setback": "m",
    "rear_setback": "m",
    "side_setback": "m",
    "parking_stalls": "count",
}


class Source(str, Enum):
    VISION = "vision"      # read by the Claude vision model
    TEXT = "text"          # read from the embedded PDF text layer
    DERIVED = "derived"    # computed by the measurement engine


class BBox(BaseModel):
    """Bounding box, normalized 0..1, top-left origin, relative to the page."""
    x0: float
    y0: float
    x1: float
    y1: float
    page: int = 0


class Field(BaseModel):
    """One extracted measurement, with honest uncertainty."""
    name: str
    value: Optional[float] = None
    unit: str = ""
    confidence: float = 0.0          # 0..1
    source: Source = Source.VISION
    bbox: Optional[BBox] = None
    note: Optional[str] = None       # e.g. "Unable to determine"

    @property
    def determined(self) -> bool:
        return self.value is not None


class SitePlan(BaseModel):
    """Everything extracted from one site-plan PDF."""
    fields: Dict[str, Field] = PydField(default_factory=dict)
    backend: str = ""                # "claude" | "local"
    source_pdf: str = ""
    page_count: int = 1
    page_width_pt: float = 0.0
    page_height_pt: float = 0.0
    warnings: List[str] = PydField(default_factory=list)

    def get(self, key: str) -> Optional[Field]:
        return self.fields.get(key)

    def set(self, field: Field) -> None:
        self.fields[field.name] = field


def undetermined(name: str, note: str = "Unable to determine") -> Field:
    """A field the extractor could not read."""
    return Field(
        name=name,
        value=None,
        unit=FIELD_UNITS.get(name, ""),
        confidence=0.0,
        note=note,
    )
