"""Environment variable loader — wraps python-dotenv, no hardcoded defaults."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


def load_env(env_file: Path | None = None) -> None:
    """Load .env file into os.environ. Must be called at app startup."""
    target = env_file or Path(__file__).parent.parent.parent / ".env"
    load_dotenv(target, override=False)


def require(key: str) -> str:
    """Return an env variable or raise if missing."""
    value = os.environ.get(key)
    if not value:
        raise EnvironmentError(f"Required environment variable '{key}' is not set.")
    return value


def get(key: str, default: str) -> str:
    """Return an env variable with a fallback default."""
    return os.environ.get(key, default)
