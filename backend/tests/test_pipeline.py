"""Extraction (local) -> measurement -> compliance, on the synthetic sample."""
from app.compliance.engine import Status, evaluate
from app.extraction.local_extractor import LocalExtractor
from app.extraction.schema import Field, SitePlan, Source
from app.measurement.engine import derive


# --- Local extraction ------------------------------------------------------
def test_local_extraction_reads_all_fields(sample_pdf):
    plan = LocalExtractor().extract(sample_pdf)
    assert plan.get("lot_width").value == 18.0
    assert plan.get("lot_depth").value == 30.0
    assert plan.get("front_setback").value == 5.2
    assert plan.get("rear_setback").value == 8.1
    assert plan.get("side_setback").value == 1.3  # governing (minimum)
    assert plan.get("building_height").value == 9.5
    assert plan.get("parking_stalls").value == 2.0
    assert plan.get("building_footprint_width").value == 13.2
    assert plan.get("building_footprint_depth").value == 16.7
    assert plan.get("building_footprint_area").value == 220.4
    # every read carries a bounding box for annotation
    assert plan.get("front_setback").bbox is not None


def test_footprint_area_derived_from_dimensions():
    plan = SitePlan()
    plan.set(Field(name="building_footprint_width", value=10.0, confidence=0.7))
    plan.set(Field(name="building_footprint_depth", value=12.0, confidence=0.9))
    derive(plan)
    area = plan.get("building_footprint_area")
    assert area.value == 120.0
    assert area.source == Source.DERIVED
    assert area.confidence == 0.7  # min of inputs


# --- Measurement -----------------------------------------------------------
def test_lot_coverage_derived(sample_pdf):
    plan = derive(LocalExtractor().extract(sample_pdf))
    coverage = plan.get("lot_coverage")
    assert coverage.source == Source.DERIVED
    assert abs(coverage.value - 40.8) < 0.2


def test_lot_area_derived_when_missing():
    plan = SitePlan()
    plan.set(Field(name="lot_width", value=20.0, confidence=0.8))
    plan.set(Field(name="lot_depth", value=25.0, confidence=0.6))
    derive(plan)
    area = plan.get("lot_area")
    assert area.value == 500.0
    assert area.source == Source.DERIVED
    assert area.confidence == 0.6  # min of inputs


def test_stated_area_inconsistent_with_dimensions_is_flagged():
    plan = SitePlan()
    plan.set(Field(name="lot_width", value=18.0, confidence=0.9))
    plan.set(Field(name="lot_depth", value=30.0, confidence=0.9))
    plan.set(Field(name="lot_area", value=400.0, confidence=0.9))  # != 540
    derive(plan)
    assert plan.get("lot_area").confidence <= 0.5
    assert plan.warnings


# --- Compliance ------------------------------------------------------------
def test_sample_matches_expected_defect_window(sample_pdf):
    report = evaluate(derive(LocalExtractor().extract(sample_pdf)))
    by_id = {r.rule_id: r for r in report.results}
    assert by_id["front_setback"].status == Status.FAIL
    assert by_id["front_setback"].deficiency == 0.8
    assert by_id["side_setback"].status == Status.FAIL
    assert by_id["side_setback"].deficiency == 0.2
    assert by_id["rear_setback"].status == Status.PASS
    assert by_id["lot_coverage"].status == Status.PASS
    assert by_id["building_height"].status == Status.PASS
    assert by_id["parking"].status == Status.PASS
    assert report.passed == 4 and report.failed == 2 and report.unknown == 0
    assert not report.compliant


def test_missing_value_is_unknown_not_fail():
    plan = SitePlan()  # nothing extracted
    report = evaluate(plan)
    assert all(r.status == Status.UNKNOWN for r in report.results)
    assert report.failed == 0
    assert report.results[0].actual == "Unable to determine"
