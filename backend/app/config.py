"""Application configuration, loaded from environment / .env."""
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BACKEND_DIR / ".env"), extra="ignore"
    )

    # "openai" (vision) or "local" (offline). The vision backend falls back to
    # "local" when its credential is not present.
    extractor: str = "openai"
    # OpenAI Console API key (sk-...). Enables the OpenAI vision backend.
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o"
    storage_dir: str = "storage"

    @property
    def has_openai_credential(self) -> bool:
        return bool(self.openai_api_key)

    @property
    def storage_path(self) -> Path:
        path = BACKEND_DIR / self.storage_dir
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def resolved_extractor(self) -> str:
        """The backend that will actually run, after fallback rules."""
        if self.extractor == "openai" and not self.has_openai_credential:
            return "local"
        return self.extractor


@lru_cache
def get_settings() -> Settings:
    return Settings()
