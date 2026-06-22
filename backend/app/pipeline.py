"""End-to-end orchestration: extract -> measure -> evaluate.

Kept separate from the web layer so it's testable on its own. Adds runtime
resilience: if the Claude backend fails mid-request (network, rate limit), it
falls back to the local backend and records why, instead of failing the request.
"""
import logging
from typing import Optional, Tuple

from .compliance.engine import ComplianceReport, evaluate
from .config import Settings, get_settings
from .extraction.base import get_extractor
from .extraction.schema import SitePlan
from .measurement.engine import derive

logger = logging.getLogger(__name__)


def analyze(pdf_path: str,
            settings: Optional[Settings] = None
            ) -> Tuple[SitePlan, ComplianceReport]:
    settings = settings or get_settings()
    extractor = get_extractor(settings)

    try:
        plan = extractor.extract(pdf_path)
    except Exception as exc:  # noqa: BLE001 - resilience over a clean stack
        if extractor.name != "claude":
            raise
        logger.warning("Claude extraction failed (%s); using local fallback",
                       exc)
        from .extraction.local_extractor import LocalExtractor
        plan = LocalExtractor().extract(pdf_path)
        plan.warnings.append(
            f"Claude extraction failed ({exc}); fell back to local backend."
        )

    derive(plan)
    report = evaluate(plan)
    return plan, report
