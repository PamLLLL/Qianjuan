from __future__ import annotations

import logging

from app.config import get_api_keys_from_env, get_settings
from app.core.ai.provider import AiProvider, AuthenticationError

logger = logging.getLogger(__name__)

_providers: dict[str, type[AiProvider]] = {}
_instances: dict[str, AiProvider] = {}


def register_provider(name: str, cls: type[AiProvider]) -> None:
    _providers[name] = cls


def get_provider(name: str | None = None) -> AiProvider:
    """Get an AI provider instance by name.

    Uses cached instances. Falls back to default provider from settings.
    """
    if name is None:
        name = get_settings().default_provider

    if name in _instances:
        return _instances[name]

    if name not in _providers:
        raise ValueError(f"未知的 AI 提供商: {name}。可用: {list(_providers.keys())}")

    api_key = _get_api_key(name)
    if not api_key:
        raise AuthenticationError(f"{name} 的 API Key 未配置，请在设置页面配置")

    model = _get_default_model(name)
    instance = _providers[name](api_key=api_key, model=model)
    _instances[name] = instance
    return instance


def clear_cache() -> None:
    """Clear provider instance cache (used after API key changes)."""
    _instances.clear()


def list_providers() -> list[dict[str, object]]:
    """List all registered providers with availability status."""
    keys = get_api_keys_from_env()
    result = []
    for name in _providers:
        key_name = _key_mapping().get(name, "")
        available = bool(keys.get(key_name, ""))
        result.append({
            "name": name,
            "display_name": _display_names().get(name, name),
            "available": available,
            "models": _model_options().get(name, []),
        })
    return result


def _get_api_key(name: str) -> str:
    keys = get_api_keys_from_env()
    key_name = _key_mapping().get(name, "")
    return keys.get(key_name, "")


def _get_default_model(name: str) -> str:
    defaults = {
        "deepseek": "deepseek-chat",
        "claude": "claude-sonnet-4-20250514",
        "openai": "gpt-4o",
        "qwen": "qwen-plus",
    }
    return defaults.get(name, "")


def _key_mapping() -> dict[str, str]:
    return {
        "deepseek": "deepseek_api_key",
        "claude": "claude_api_key",
        "openai": "openai_api_key",
        "qwen": "dashscope_api_key",
    }


def _display_names() -> dict[str, str]:
    return {
        "deepseek": "DeepSeek",
        "claude": "Claude (Anthropic)",
        "openai": "GPT (OpenAI)",
        "qwen": "通义千问",
    }


def _model_options() -> dict[str, list[str]]:
    return {
        "deepseek": ["deepseek-chat", "deepseek-reasoner"],
        "claude": ["claude-sonnet-4-20250514", "claude-haiku-4-5-20251001"],
        "openai": ["gpt-4o", "gpt-4o-mini"],
        "qwen": ["qwen-plus", "qwen-turbo", "qwen-max"],
    }


def _register_defaults() -> None:
    from app.core.ai.deepseek import DeepSeekProvider
    from app.core.ai.claude import ClaudeProvider
    from app.core.ai.openai_provider import OpenAIProvider
    from app.core.ai.qwen import QwenProvider

    register_provider("deepseek", DeepSeekProvider)
    register_provider("claude", ClaudeProvider)
    register_provider("openai", OpenAIProvider)
    register_provider("qwen", QwenProvider)


_register_defaults()
