"""Extractor interface and backend selection.

The pipeline depends only on this interface, so the perception layer is fully
swappable: OpenAI vision when available, a fully offline local backend
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
    """Pick a backend, falling back to local when OpenAI is unavailable."""
    settings = settings or get_settings()

    if settings.extractor == "openai":
        if settings.has_openai_credential:
            from .openai_extractor import OpenAIExtractor
            return OpenAIExtractor(
                model=settings.openai_model,
                api_key=settings.openai_api_key,
            )
        logger.warning(
            "EXTRACTOR=openai but no OPENAI_API_KEY is set; falling back to "
            "the local extractor."
        )

    from .local_extractor import LocalExtractor
    return LocalExtractor()
