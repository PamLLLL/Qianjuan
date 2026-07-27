from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class AiError(Exception):
    """Base exception for AI provider errors."""


class RateLimitError(AiError):
    """429 Too Many Requests."""


class ServerError(AiError):
    """5xx Server Error."""


class AuthenticationError(AiError):
    """401 Unauthorized."""


class MaxRetriesExceeded(AiError):
    """All retry attempts exhausted."""


@dataclass
class AiUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""


class AiProvider(ABC):
    """Abstract base class for AI model providers.

    Subclasses must implement _do_generate() and _do_stream_generate().
    Retry logic is handled by this base class.
    """

    MAX_RETRIES = 3
    RETRY_BASE_DELAY = 1.0

    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model
        self.last_usage: AiUsage | None = None

    @property
    @abstractmethod
    def provider_name(self) -> str:
        ...

    @abstractmethod
    async def _do_generate(self, system_prompt: str, user_prompt: str) -> tuple[str, AiUsage]:
        ...

    @abstractmethod
    async def _do_stream_generate(
        self, system_prompt: str, user_prompt: str
    ) -> AsyncGenerator[str, None]:
        ...

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Generate a complete response with retry logic."""
        result, usage = await self._call_with_retry(
            self._do_generate, system_prompt, user_prompt
        )
        self.last_usage = usage
        return result

    async def stream_generate(
        self, system_prompt: str, user_prompt: str
    ) -> AsyncGenerator[str, None]:
        """Stream generate tokens. No retry on stream — caller should retry."""
        async for chunk in self._do_stream_generate(system_prompt, user_prompt):
            yield chunk

    async def _call_with_retry(self, func, *args):
        last_exc = None
        for attempt in range(self.MAX_RETRIES):
            try:
                return await func(*args)
            except RateLimitError as e:
                last_exc = e
                delay = self.RETRY_BASE_DELAY * (4 ** attempt)
                logger.warning(
                    "Rate limited (attempt %d/%d), retrying in %.1fs",
                    attempt + 1, self.MAX_RETRIES, delay,
                )
                await asyncio.sleep(delay)
            except ServerError as e:
                last_exc = e
                if attempt < 1:
                    logger.warning("Server error (attempt %d), retrying in 3s", attempt + 1)
                    await asyncio.sleep(3)
                else:
                    raise
            except AuthenticationError:
                raise
        raise MaxRetriesExceeded(f"All {self.MAX_RETRIES} retries exhausted") from last_exc
