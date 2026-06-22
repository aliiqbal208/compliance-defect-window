import os
import sys
from pathlib import Path

import pytest

# Keep the suite deterministic and offline regardless of any .env credential:
# env vars take precedence over .env in pydantic-settings.
os.environ["EXTRACTOR"] = "local"

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "sample_data"))

import generate_sample  # noqa: E402


@pytest.fixture(scope="session")
def sample_pdf(tmp_path_factory) -> str:
    out = tmp_path_factory.mktemp("data") / "plan.pdf"
    generate_sample.build(out)
    return str(out)
