from __future__ import annotations

import fcntl
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import BASE_DIR, clear_api_key_cache, get_api_keys_from_env
from app.core.ai import registry
from app.core.ai.provider import AiError
from app.database import get_session
from app.models.global_config import GlobalConfig
from app.schemas.settings import (
    ApiKeyStatus,
    ApiKeyUpdate,
    GlobalConfigResponse,
    GlobalConfigUpdate,
    ProviderInfo,
)

router = APIRouter(prefix="/api/settings", tags=["settings"])


async def _get_or_create_config(session: AsyncSession) -> GlobalConfig:
    config = await session.get(GlobalConfig, 1)
    if not config:
        config = GlobalConfig(id=1)
        session.add(config)
        await session.flush()
    return config


@router.get("", response_model=GlobalConfigResponse)
async def get_settings(session: AsyncSession = Depends(get_session)):
    config = await _get_or_create_config(session)
    return GlobalConfigResponse.model_validate(config)


@router.put("", response_model=GlobalConfigResponse)
async def update_settings(
    data: GlobalConfigUpdate,
    session: AsyncSession = Depends(get_session),
):
    config = await _get_or_create_config(session)
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(config, key, value)
    await session.flush()
    await session.refresh(config)
    return GlobalConfigResponse.model_validate(config)


@router.get("/api-keys", response_model=ApiKeyStatus)
async def get_api_key_status():
    keys = get_api_keys_from_env()
    return ApiKeyStatus(
        deepseek=bool(keys.get("deepseek_api_key")),
        claude=bool(keys.get("claude_api_key")),
        openai=bool(keys.get("openai_api_key")),
        dashscope=bool(keys.get("dashscope_api_key")),
    )


@router.put("/api-keys")
async def update_api_keys(data: ApiKeyUpdate):
    env_path = BASE_DIR / ".env"
    updates = data.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="没有提供任何 API Key")

    _write_env_keys(env_path, {k.upper(): v for k, v in updates.items() if v})
    clear_api_key_cache()
    registry.clear_cache()
    return {"message": "API Key 已更新", "updated": list(updates.keys())}


@router.get("/providers", response_model=list[ProviderInfo])
async def get_providers():
    providers = registry.list_providers()
    return [ProviderInfo(**p) for p in providers]


@router.post("/test-connection/{provider_name}")
async def test_connection(provider_name: str):
    """Test if an AI provider's API key is valid and the service is reachable."""
    try:
        provider = registry.get_provider(provider_name)
    except (ValueError, AiError) as e:
        return {"success": False, "provider": provider_name, "error": str(e)}

    try:
        response = await provider.generate(
            system_prompt="你是一个测试助手。",
            user_prompt="请回复'连接成功'四个字。",
        )
        return {
            "success": True,
            "provider": provider_name,
            "model": provider.model,
            "response": response[:100],
        }
    except AiError as e:
        return {"success": False, "provider": provider_name, "error": str(e)}
    except Exception as e:
        return {"success": False, "provider": provider_name, "error": f"连接失败: {type(e).__name__}: {e}"}


def _write_env_keys(env_path: Path, updates: dict[str, str]) -> None:
    """Write API keys to .env file with file locking."""
    env_path.touch(exist_ok=True)

    with open(env_path, "r+", encoding="utf-8") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            lines = f.readlines()
            existing_keys = set()
            new_lines = []

            for line in lines:
                stripped = line.strip()
                if stripped and not stripped.startswith("#") and "=" in stripped:
                    key = stripped.split("=", 1)[0].strip()
                    if key in updates:
                        new_lines.append(f"{key}={updates[key]}\n")
                        existing_keys.add(key)
                        continue
                new_lines.append(line)

            for key, value in updates.items():
                if key not in existing_keys:
                    new_lines.append(f"{key}={value}\n")

            f.seek(0)
            f.truncate()
            f.writelines(new_lines)
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
