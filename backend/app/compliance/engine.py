"""Compliance engine: evaluate extracted values against the zoning rules.

Pure comparison. Each rule produces a CheckResult. A value that wasn't read is
UNKNOWN, not FAIL, so the user can tell "this breaks the bylaw" apart from "we
couldn't read this". Failures carry the deficiency amount and a bounding box, so
the defect window and the annotation can both point at the problem.
"""
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel

from ..extraction.schema import BBox, SitePlan
from .rules import RULES, Op, Rule


class Status(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"   # value could not be determined


class CheckResult(BaseModel):
    rule_id: str
    label: str
    field: str
    required: str
    actual: Optional[str] = None        # display string, or None if unknown
    actual_value: Optional[float] = None
    status: Status = Status.UNKNOWN
    deficiency: Optional[float] = None   # how far short / over, when FAIL
    message: Optional[str] = None        # e.g. "deficient by 0.8 m"
    confidence: float = 0.0
    bbox: Optional[BBox] = None


class ComplianceReport(BaseModel):
    results: List[CheckResult]
    passed: int
    failed: int
    unknown: int

    @property
    def compliant(self) -> bool:
        return self.failed == 0 and self.unknown == 0


def evaluate(plan: SitePlan, rules: List[Rule] = None) -> ComplianceReport:
    rules = rules if rules is not None else RULES
    results = [_check(plan, rule) for rule in rules]
    return ComplianceReport(
        results=results,
        passed=sum(r.status == Status.PASS for r in results),
        failed=sum(r.status == Status.FAIL for r in results),
        unknown=sum(r.status == Status.UNKNOWN for r in results),
    )


def _check(plan: SitePlan, rule: Rule) -> CheckResult:
    field = plan.get(rule.field)
    base = CheckResult(
        rule_id=rule.id, label=rule.label, field=rule.field,
        required=rule.required_text(),
    )

    if not field or not field.determined:
        base.status = Status.UNKNOWN
        base.actual = "Unable to determine"
        base.message = "Value could not be extracted"
        return base

    base.actual_value = field.value
    base.actual = _fmt(field.value, rule.unit)
    base.confidence = field.confidence
    base.bbox = field.bbox

    if rule.op == Op.GTE:
        ok = field.value >= rule.threshold
        short = rule.threshold - field.value
    else:
        ok = field.value <= rule.threshold
        short = field.value - rule.threshold

    if ok:
        base.status = Status.PASS
    else:
        base.status = Status.FAIL
        base.deficiency = round(short, 2)
        base.message = _deficiency_message(rule, short)
    return base


def _fmt(value: float, unit: str) -> str:
    if unit == "count":
        return f"{int(value)}"
    if unit == "%":
        return f"{value:g}%"
    return f"{value:g} {unit}"


def _deficiency_message(rule: Rule, short: float) -> str:
    amount = round(abs(short), 2)
    if rule.op == Op.GTE:
        if rule.unit == "count":
            return f"{rule.label} short by {int(amount)}"
        if rule.unit == "%":
            return f"{rule.label} short by {amount:g}%"
        return f"{rule.label} deficient by {amount:g} m"
    if rule.unit == "%":
        return f"{rule.label} exceeds limit by {amount:g}%"
    return f"{rule.label} exceeds limit by {amount:g} {rule.unit}"
