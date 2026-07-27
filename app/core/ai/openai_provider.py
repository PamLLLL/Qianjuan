from __future__ import annotations

import logging
from collections.abc import AsyncGenerator

from openai import AsyncOpenAI, APIStatusError

from app.core.ai.provider import (
    AiProvider,
    AiUsage,
    AuthenticationError,
    RateLimitError,
    ServerError,
)

logger = logging.getLogger(__name__)


class OpenAIProvider(AiProvider):
    """GPT (OpenAI) AI provider."""

    def __init__(self, api_key: str, model: str = "gpt-4o") -> None:
        super().__init__(api_key, model)
        self.client = AsyncOpenAI(api_key=api_key)

    @property
    def provider_name(self) -> str:
        return "openai"

    async def _do_generate(self, system_prompt: str, user_prompt: str) -> tuple[str, AiUsage]:
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,
                max_tokens=8192,
            )
        except APIStatusError as e:
            self._handle_api_error(e)

        choice = response.choices[0]
        content = choice.message.content or ""
        usage = AiUsage(
            input_tokens=response.usage.prompt_tokens if response.usage else 0,
            output_tokens=response.usage.completion_tokens if response.usage else 0,
            model=response.model,
        )
        return content, usage

    async def _do_stream_generate(
        self, system_prompt: str, user_prompt: str
    ) -> AsyncGenerator[str, None]:
        try:
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,
                max_tokens=8192,
                stream=True,
            )
        except APIStatusError as e:
            self._handle_api_error(e)

        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def _handle_api_error(self, e: APIStatusError) -> None:
        if e.status_code == 401:
            raise AuthenticationError("OpenAI API Key 无效或已过期") from e
        if e.status_code == 429:
            raise RateLimitError("OpenAI API 请求频率超限") from e
        if e.status_code >= 500:
            raise ServerError(f"OpenAI 服务器错误: {e.status_code}") from e
        raise
