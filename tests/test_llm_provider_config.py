from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from app.llm.client import (
    AGNES_DEFAULT_BASE_URL,
    AGNES_DEFAULT_MODEL,
    GEMINI_OPENAI_BASE_URL,
    LLMClient,
    _gemini_native_error,
    resolve_llm_provider_settings,
)
from app.llm.errors import LLMProviderError


def test_resolve_gemini_provider_uses_openai_compatible_defaults():
    settings = SimpleNamespace(
        llm_provider="gemini",
        llm_api_key="dashscope-key",
        gemini_api_key="gemini-key",
        llm_base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        llm_model_brain="qwen-max",
        llm_model_vision="qwen-vl-max",
        llm_model_chat="qwen-plus",
    )

    resolved = resolve_llm_provider_settings(settings)

    assert resolved["provider"] == "gemini"
    assert resolved["api_key"] == "gemini-key"
    assert resolved["base_url"] == GEMINI_OPENAI_BASE_URL
    assert resolved["model_brain"] == "gemini-2.5-flash"
    assert resolved["model_vision"] == "gemini-2.5-flash"
    assert resolved["model_chat"] == "gemini-2.5-flash"


def test_resolve_gemini_provider_does_not_reuse_dashscope_key():
    settings = SimpleNamespace(
        llm_provider="gemini",
        llm_api_key="dashscope-key",
        gemini_api_key="",
        llm_base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        llm_model_brain="qwen-max",
        llm_model_vision="qwen-vl-max",
        llm_model_chat="qwen-plus",
    )

    resolved = resolve_llm_provider_settings(settings)

    assert resolved["provider"] == "gemini"
    assert resolved["api_key"] == ""


def test_resolve_dashscope_provider_keeps_existing_models():
    settings = SimpleNamespace(
        llm_provider="bailian",
        llm_api_key="dashscope-key",
        gemini_api_key="",
        llm_base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        llm_model_brain="qwen-max",
        llm_model_vision="qwen-vl-max",
        llm_model_chat="qwen-plus",
    )

    resolved = resolve_llm_provider_settings(settings)

    assert resolved["provider"] == "dashscope"
    assert resolved["api_key"] == "dashscope-key"
    assert resolved["model_brain"] == "qwen-max"


def test_resolve_agnes_provider_uses_openai_compatible_defaults():
    settings = SimpleNamespace(
        llm_provider="agnes",
        llm_api_key="agnes-key",
        gemini_api_key="",
        llm_base_url="",
        llm_model_brain="qwen-max",
        llm_model_vision="qwen-vl-max",
        llm_model_chat="qwen-plus",
    )

    resolved = resolve_llm_provider_settings(settings)

    assert resolved["provider"] == "agnes"
    assert resolved["api_key"] == "agnes-key"
    assert resolved["base_url"] == AGNES_DEFAULT_BASE_URL
    assert resolved["model_brain"] == AGNES_DEFAULT_MODEL
    assert resolved["model_vision"] == AGNES_DEFAULT_MODEL
    assert resolved["model_chat"] == AGNES_DEFAULT_MODEL


def test_llm_client_uses_configured_sdk_retry_count():
    client = LLMClient(api_key="test-key", provider="gemini", sdk_max_retries=0)

    assert client.client.max_retries == 0


@pytest.mark.asyncio
async def test_gemini_text_chat_uses_native_endpoint(monkeypatch):
    client = LLMClient(api_key="test-key", provider="gemini", model_chat="gemini-2.5-flash")
    native_chat = AsyncMock(return_value={"content": "ok", "model": "gemini-2.5-flash"})
    monkeypatch.setattr(client, "_gemini_native_chat", native_chat)

    result = await client.chat([{"role": "user", "content": "ping"}])

    assert result["content"] == "ok"
    native_chat.assert_awaited_once()


@pytest.mark.asyncio
async def test_gemini_tool_chat_uses_openai_compatible_endpoint(monkeypatch):
    client = LLMClient(api_key="test-key", provider="gemini", model_chat="gemini-2.5-flash")
    completion = Mock()
    completion.choices = [Mock(message=Mock(content="ok", tool_calls=None), finish_reason="stop")]
    completion.usage = Mock(prompt_tokens=1, completion_tokens=1, total_tokens=2)
    client.client.chat.completions.create = AsyncMock(return_value=completion)

    result = await client.chat(
        [{"role": "user", "content": "ping"}],
        tools=[{"type": "function", "function": {"name": "noop", "parameters": {"type": "object"}}}],
    )

    assert result["content"] == "ok"
    client.client.chat.completions.create.assert_awaited_once()


def test_gemini_native_error_parses_rate_limit_retry_delay():
    error = _gemini_native_error(
        {
            "error": {
                "code": 429,
                "message": "Quota exceeded. Please retry in 13.301235794s.",
                "status": "RESOURCE_EXHAUSTED",
            }
        },
        status_code=429,
        provider="gemini",
    )

    assert error.code == "rate_limited"
    assert error.retry_after_seconds == 13.301235794


@pytest.mark.asyncio
async def test_llm_client_rejects_missing_api_key_before_provider_call():
    client = LLMClient(api_key="", provider="gemini", model_chat="gemini-2.5-flash")

    with pytest.raises(LLMProviderError) as exc:
        await client.chat([{"role": "user", "content": "ping"}])

    assert exc.value.code == "missing_api_key"
    assert exc.value.provider == "gemini"
