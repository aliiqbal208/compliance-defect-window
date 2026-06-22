"""Zoning rules as configuration.

A new bylaw is a new entry here, not new code. Each rule names the SitePlan field
it reads, a comparison, and a threshold. The sample values come straight from the
assessment.
"""
from enum import Enum
from typing import List

from pydantic import BaseModel


class Op(str, Enum):
    GTE = ">="   # actual must be at least the threshold
    LTE = "<="   # actual must be at most the threshold


class Rule(BaseModel):
    id: str
    label: str
    field: str        # SitePlan field key this rule reads
    op: Op
    threshold: float
    unit: str

    def required_text(self) -> str:
        sign = "≥" if self.op == Op.GTE else "≤"  # ≥ / ≤
        if self.unit == "count":
            return f"{sign} {int(self.threshold)}"
        if self.unit == "%":
            return f"{sign} {self.threshold:g}%"
        return f"{sign} {self.threshold:.1f} {self.unit}"


RULES: List[Rule] = [
    Rule(id="front_setback", label="Front Setback",
         field="front_setback", op=Op.GTE, threshold=6.0, unit="m"),
    Rule(id="rear_setback", label="Rear Setback",
         field="rear_setback", op=Op.GTE, threshold=7.5, unit="m"),
    Rule(id="side_setback", label="Side Setback",
         field="side_setback", op=Op.GTE, threshold=1.5, unit="m"),
    Rule(id="lot_coverage", label="Lot Coverage",
         field="lot_coverage", op=Op.LTE, threshold=45.0, unit="%"),
    Rule(id="building_height", label="Building Height",
         field="building_height", op=Op.LTE, threshold=10.0, unit="m"),
    Rule(id="parking", label="Parking",
         field="parking_stalls", op=Op.GTE, threshold=2.0, unit="count"),
]
