from __future__ import annotations

from collections.abc import AsyncGenerator


MOCK_DEFAULT_JSON = '{"result": "mock AI response"}'
MOCK_CHARACTERS_JSON = '[{"name": "测试角色", "role": "protagonist", "personality": "勇敢"}]'
MOCK_OUTLINE_JSON = '{"premise": "测试故事前提", "act_one": {"title": "第一幕"}}'


class MockAiProvider:
    """Test mock that returns preset JSON without calling any real API."""

    async def generate(self, system_prompt: str, user_prompt: str, **kwargs: object) -> str:
        if "人物" in user_prompt or "角色" in user_prompt:
            return MOCK_CHARACTERS_JSON
        if "大纲" in user_prompt:
            return MOCK_OUTLINE_JSON
        return MOCK_DEFAULT_JSON

    async def stream_generate(
        self, system_prompt: str, user_prompt: str, **kwargs: object
    ) -> AsyncGenerator[str, None]:
        result = await self.generate(system_prompt, user_prompt, **kwargs)
        for char in result:
            yield char
