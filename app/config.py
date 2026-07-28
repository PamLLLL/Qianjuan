from __future__ import annotations

import os
import time
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent
RULES_DIR = BASE_DIR / "rules"
DATA_DIR = BASE_DIR / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "千卷 QianJuan"
    debug: bool = True

    database_url: str = f"sqlite+aiosqlite:///{DATA_DIR / 'qianjuan.db'}"

    deepseek_api_key: str = ""
    claude_api_key: str = ""
    openai_api_key: str = ""
    dashscope_api_key: str = ""

    default_provider: str = "deepseek"
    default_model: str = "deepseek-chat"


@lru_cache
def get_settings() -> Settings:
    return Settings()


_api_key_cache: dict[str, tuple[float, dict[str, str]]] = {}
API_KEY_CACHE_TTL = 60.0


PLACEHOLDER_VALUES = {"sk-xxx", "sk-ant-xxx", ""}


def get_api_keys_from_env() -> dict[str, str]:
    """Read API keys from .env file with 60-second cache for hot reload."""
    cache_key = "api_keys"
    now = time.time()

    if cache_key in _api_key_cache:
        cached_time, cached_keys = _api_key_cache[cache_key]
        if now - cached_time < API_KEY_CACHE_TTL:
            return cached_keys

    env_path = BASE_DIR / ".env"
    keys: dict[str, str] = {}
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip()
                if key.endswith("_API_KEY") and value not in PLACEHOLDER_VALUES:
                    keys[key.lower()] = value

    _api_key_cache[cache_key] = (now, keys)
    return keys


def clear_api_key_cache() -> None:
    """Clear the API key cache. Call after writing to .env."""
    _api_key_cache.clear()
