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

    # "claude" (vision) or "local" (offline). Falls back to "local" when the
    # Claude backend is requested but no credential is present.
    extractor: str = "claude"
    # A Console API key (sk-ant-api..., sent as x-api-key) OR ...
    anthropic_api_key: Optional[str] = None
    # ... an OAuth token from `claude setup-token` (sk-ant-oat..., sent as a
    # Bearer token). Either one enables the Claude backend.
    anthropic_auth_token: Optional[str] = None
    claude_model: str = "claude-opus-4-8"
    storage_dir: str = "storage"

    @property
    def has_claude_credential(self) -> bool:
        return bool(self.anthropic_api_key or self.anthropic_auth_token)

    @property
    def storage_path(self) -> Path:
        path = BACKEND_DIR / self.storage_dir
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def resolved_extractor(self) -> str:
        """The backend that will actually run, after fallback rules."""
        if self.extractor == "claude" and not self.has_claude_credential:
            return "local"
        return self.extractor


@lru_cache
def get_settings() -> Settings:
    return Settings()
