"""Extractor interface and backend selection.

The pipeline depends only on this interface, so the perception layer is fully
swappable: Claude vision when available, a fully offline local backend
otherwise. Selection and graceful fallback live here.
"""
import logging
from typing import Protocol

from ..config import Settings, get_settings
from .schema import SitePlan

logger = logging.getLogger(__name__)


class Extractor(Protocol):
    name: str

    def extract(self, pdf_path: str) -> SitePlan:
        ...


def get_extractor(settings: Settings = None) -> Extractor:
    """Pick a backend, falling back to local when Claude is unavailable."""
    settings = settings or get_settings()

    if settings.extractor == "claude":
        if settings.has_claude_credential:
            from .vision_extractor import VisionExtractor
            return VisionExtractor(
                model=settings.claude_model,
                api_key=settings.anthropic_api_key,
                auth_token=settings.anthropic_auth_token,
            )
        logger.warning(
            "EXTRACTOR=claude but no ANTHROPIC_API_KEY or ANTHROPIC_AUTH_TOKEN "
            "is set; falling back to the local extractor."
        )

    from .local_extractor import LocalExtractor
    return LocalExtractor()
