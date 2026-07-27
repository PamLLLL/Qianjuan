from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class GlobalConfigResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    default_provider: str
    default_model: str
    ui_preferences: dict | None


class GlobalConfigUpdate(BaseModel):
    default_provider: str | None = None
    default_model: str | None = None
    ui_preferences: dict | None = None


class ApiKeyStatus(BaseModel):
    deepseek: bool = False
    claude: bool = False
    openai: bool = False
    dashscope: bool = False


class ApiKeyUpdate(BaseModel):
    deepseek_api_key: str | None = None
    claude_api_key: str | None = None
    openai_api_key: str | None = None
    dashscope_api_key: str | None = None


class ProviderInfo(BaseModel):
    name: str
    display_name: str
    available: bool
    models: list[str]
