from __future__ import annotations

import logging
from collections.abc import AsyncGenerator

from anthropic import AsyncAnthropic, APIStatusError

from app.core.ai.provider import (
    AiProvider,
    AiUsage,
    AuthenticationError,
    RateLimitError,
    ServerError,
)

logger = logging.getLogger(__name__)


class ClaudeProvider(AiProvider):
    """Claude (Anthropic) AI provider."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514") -> None:
        super().__init__(api_key, model)
        self.client = AsyncAnthropic(api_key=api_key)

    @property
    def provider_name(self) -> str:
        return "claude"

    async def _do_generate(self, system_prompt: str, user_prompt: str) -> tuple[str, AiUsage]:
        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=8192,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
        except APIStatusError as e:
            self._handle_api_error(e)

        content = response.content[0].text if response.content else ""
        usage = AiUsage(
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            model=response.model,
        )
        return content, usage

    async def _do_stream_generate(
        self, system_prompt: str, user_prompt: str
    ) -> AsyncGenerator[str, None]:
        try:
            async with self.client.messages.stream(
                model=self.model,
                max_tokens=8192,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            ) as stream:
                async for text in stream.text_stream:
                    yield text
        except APIStatusError as e:
            self._handle_api_error(e)

    def _handle_api_error(self, e: APIStatusError) -> None:
        if e.status_code == 401:
            raise AuthenticationError("Claude API Key 无效或已过期") from e
        if e.status_code == 429:
            raise RateLimitError("Claude API 请求频率超限") from e
        if e.status_code >= 500:
            raise ServerError(f"Claude 服务器错误: {e.status_code}") from e
        raise
