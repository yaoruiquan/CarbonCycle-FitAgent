"""
LLM client wrapper with multi-model support.
支持多模型的 LLM 客户端封装

Provides unified interface for different LLM models:
为不同的 LLM 模型提供统一接口：
- Brain (Qwen-Max): Complex planning and reasoning / 复杂规划和推理
- Vision (Qwen-VL-Max): Image understanding, OCR / 图像理解，OCR
- Chat (Qwen-Plus): Daily conversation, text generation / 日常对话，文本生成
"""

import base64
import re
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional, Union

import httpx
from openai import AsyncOpenAI

from app.core.config import get_settings
from app.core.logging import get_logger
from app.llm.errors import LLMProviderError, classify_llm_exception

logger = get_logger(__name__)


GEMINI_OPENAI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
GEMINI_DEFAULT_MODEL = "gemini-2.5-flash"
DASHSCOPE_DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
AGNES_DEFAULT_BASE_URL = "https://apihub.agnes-ai.com/v1"
AGNES_DEFAULT_MODEL = "agnes-2.0-flash"


def _retry_after_from_message(message: str) -> Optional[float]:
    match = re.search(r"retry in ([0-9]+(?:\.[0-9]+)?)s", message, flags=re.IGNORECASE)
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def _gemini_native_error(data: dict[str, Any], *, status_code: int, provider: str) -> LLMProviderError:
    error = data.get("error") if isinstance(data.get("error"), dict) else {}
    message = str(error.get("message") or "Gemini API request failed.")
    provider_code = str(error.get("status") or error.get("code") or "provider_error")
    error_type = provider_code
    code = provider_code
    if status_code == 401:
        code = "unauthorized"
        error_type = "authentication_error"
        message = "模型供应商认证失败：请检查 GEMINI_API_KEY 是否有效。"
    elif status_code == 429:
        code = "rate_limited"
        error_type = "rate_limit_error"
        message = "模型供应商限流：请求过多或额度不足，请稍后重试。"
    return LLMProviderError(
        message=message,
        code=code,
        error_type=error_type,
        status_code=status_code,
        provider=provider,
        retry_after_seconds=_retry_after_from_message(str(error.get("message") or "")),
    )


class ModelType(str, Enum):
    """Available model types for different tasks."""
    BRAIN = "brain"    # Complex planning, reasoning (qwen-max)
    VISION = "vision"  # Image understanding, OCR (qwen-vl-max)
    CHAT = "chat"      # Daily conversation (qwen-plus)


class LLMClient:
    """
    Unified LLM client supporting multiple Qwen models.
    
    Automatically selects the appropriate model based on task type.
    All calls are logged for auditing purposes.
    """
    
    def __init__(
        self,
        api_key: str,
        provider: str = "dashscope",
        base_url: Optional[str] = None,
        model_brain: str = "qwen-max",
        model_vision: str = "qwen-vl-max",
        model_chat: str = "qwen-plus",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        sdk_max_retries: int = 0,
    ) -> None:
        """
        Initialize LLM client with multi-model support.
        
        Args:
            api_key: API key for Aliyun Bailian.
            base_url: API endpoint URL.
            model_brain: Model for complex reasoning.
            model_vision: Model for vision tasks.
            model_chat: Model for chat/text generation.
            temperature: Default generation temperature.
            max_tokens: Default maximum response tokens.
        """
        self.api_key_configured = bool(api_key)
        self.api_key = api_key
        self.provider = provider
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            max_retries=sdk_max_retries,
        )
        self.models = {
            ModelType.BRAIN: model_brain,
            ModelType.VISION: model_vision,
            ModelType.CHAT: model_chat,
        }
        self.temperature = temperature
        self.max_tokens = max_tokens
    
    def _get_model(self, model_type: ModelType) -> str:
        """Get model identifier for given type."""
        return self.models.get(model_type, self.models[ModelType.CHAT])
    
    async def chat(
        self,
        messages: list[dict[str, Any]],
        model_type: ModelType = ModelType.CHAT,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        tools: Optional[list[dict[str, Any]]] = None,
        tool_choice: Optional[Union[str, dict[str, Any]]] = None,
    ) -> dict[str, Any]:
        """
        Send chat completion request.
        
        Args:
            messages: List of message dicts with 'role' and 'content'.
            model_type: Which model to use (BRAIN, VISION, CHAT).
            temperature: Override default temperature.
            max_tokens: Override default max tokens.
            tools: Optional tool definitions for function calling.
            tool_choice: Tool selection strategy.
            
        Returns:
            dict containing 'content' and optionally 'tool_calls'.
        """
        model = self._get_model(model_type)
        if not self.api_key_configured:
            raise LLMProviderError(
                message=f"未配置 {self.provider} API key。",
                code="missing_api_key",
                error_type="configuration_error",
                provider=self.provider,
            )

        if self.provider == "gemini" and not tools:
            return await self._gemini_native_chat(
                messages=messages,
                model=model,
                temperature=temperature or self.temperature,
                max_tokens=max_tokens or self.max_tokens,
            )
        
        request_params = {
            "model": model,
            "messages": messages,
            "temperature": temperature or self.temperature,
            "max_tokens": max_tokens or self.max_tokens,
        }
        
        if tools:
            request_params["tools"] = tools
            if tool_choice:
                request_params["tool_choice"] = tool_choice
        
        logger.debug(
            f"LLM request: model={model}, type={model_type.value}, "
            f"messages_count={len(messages)}, has_tools={tools is not None}"
        )
        
        try:
            response = await self.client.chat.completions.create(**request_params)
            
            result = {
                "content": response.choices[0].message.content,
                "finish_reason": response.choices[0].finish_reason,
                "model": model,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                } if response.usage else None,
            }
            
            # Handle tool calls
            if response.choices[0].message.tool_calls:
                result["tool_calls"] = [
                    {
                        "id": tc.id,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in response.choices[0].message.tool_calls
                ]
            
            logger.debug(
                f"LLM response: model={model}, "
                f"tokens={result.get('usage', {}).get('total_tokens', 'N/A')}"
            )
            
            return result
            
        except Exception as e:
            provider_error = classify_llm_exception(e, provider=self.provider)
            logger.error(f"LLM API error: {provider_error}")
            raise provider_error from e

    async def _gemini_native_chat(
        self,
        *,
        messages: list[dict[str, Any]],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> dict[str, Any]:
        """Call Gemini's native REST API for non-tool text generation."""
        system_parts: list[dict[str, str]] = []
        contents: list[dict[str, Any]] = []

        for message in messages:
            content = message.get("content", "")
            text = content if isinstance(content, str) else str(content)
            if message.get("role") == "system":
                system_parts.append({"text": text})
                continue
            role = "model" if message.get("role") == "assistant" else "user"
            contents.append({"role": role, "parts": [{"text": text}]})

        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }
        if system_parts:
            payload["systemInstruction"] = {"parts": system_parts}

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(url, params={"key": self.api_key}, json=payload)
            data = response.json()
            if response.status_code >= 400:
                raise _gemini_native_error(data, status_code=response.status_code, provider=self.provider)

            candidate = (data.get("candidates") or [{}])[0]
            parts = ((candidate.get("content") or {}).get("parts") or [])
            content = "".join(part.get("text", "") for part in parts if isinstance(part, dict))
            usage = data.get("usageMetadata") or {}
            return {
                "content": content,
                "finish_reason": candidate.get("finishReason"),
                "model": model,
                "usage": {
                    "prompt_tokens": usage.get("promptTokenCount", 0),
                    "completion_tokens": usage.get("candidatesTokenCount", 0),
                    "total_tokens": usage.get("totalTokenCount", 0),
                },
            }
        except LLMProviderError:
            raise
        except Exception as e:
            provider_error = classify_llm_exception(e, provider=self.provider)
            logger.error(f"Gemini native API error: {provider_error}")
            raise provider_error from e
    
    async def plan(
        self,
        messages: list[dict[str, str]],
        tools: Optional[list[dict[str, Any]]] = None,
    ) -> dict[str, Any]:
        """
        Use Brain model for complex planning and reasoning.
        
        Args:
            messages: Conversation messages.
            tools: Optional tool definitions.
            
        Returns:
            LLM response dict.
        """
        return await self.chat(
            messages=messages,
            model_type=ModelType.BRAIN,
            tools=tools,
            temperature=0.3,  # Lower temperature for planning
        )
    
    async def analyze_image(
        self,
        image_path: Union[str, Path],
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Use Vision model for image understanding.
        
        Args:
            image_path: Path to image file.
            prompt: Question about the image.
            system_prompt: Optional system instruction.
            
        Returns:
            LLM response with image analysis.
        """
        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")
        
        # Read and encode image
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")
        
        # Determine MIME type
        suffix = image_path.suffix.lower()
        mime_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }
        mime_type = mime_types.get(suffix, "image/jpeg")
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{mime_type};base64,{image_data}"
                    }
                },
                {"type": "text", "text": prompt}
            ]
        })
        
        return await self.chat(
            messages=messages,
            model_type=ModelType.VISION,
        )
    
    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """
        Simple text generation using Chat model.
        
        Args:
            prompt: User prompt.
            system_prompt: Optional system instruction.
            temperature: Override default temperature.
            
        Returns:
            Generated text string.
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        result = await self.chat(
            messages=messages,
            model_type=ModelType.CHAT,
            temperature=temperature,
        )
        return result.get("content", "")
    
    async def stream_chat(
        self,
        messages: list[dict[str, Any]],
        model_type: ModelType = ModelType.CHAT,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ):
        """
        Stream chat completion response.
        流式返回聊天回复
        
        Args:
            messages: List of message dicts with 'role' and 'content'.
            model_type: Which model to use.
            temperature: Override default temperature.
            max_tokens: Override default max tokens.
            
        Yields:
            str: Content chunks as they arrive.
        """
        model = self._get_model(model_type)
        if not self.api_key_configured:
            raise LLMProviderError(
                message=f"未配置 {self.provider} API key。",
                code="missing_api_key",
                error_type="configuration_error",
                provider=self.provider,
            )
        
        request_params = {
            "model": model,
            "messages": messages,
            "temperature": temperature or self.temperature,
            "max_tokens": max_tokens or self.max_tokens,
            "stream": True,
        }
        
        logger.debug(f"LLM stream request: model={model}")
        
        try:
            stream = await self.client.chat.completions.create(**request_params)
            
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            provider_error = classify_llm_exception(e, provider=self.provider)
            logger.error(f"LLM stream error: {provider_error}")
            raise provider_error from e


# Singleton client instance
_llm_client: Optional[LLMClient] = None


def resolve_llm_provider_settings(settings: Any) -> dict[str, str]:
    """Resolve provider-specific OpenAI-compatible settings."""
    provider = (getattr(settings, "llm_provider", "") or "bailian").lower()
    base_url = settings.llm_base_url or None
    model_brain = settings.llm_model_brain
    model_vision = settings.llm_model_vision
    model_chat = settings.llm_model_chat
    api_key = settings.llm_api_key

    if provider in {"gemini", "google", "google_ai"}:
        provider = "gemini"
        api_key = getattr(settings, "gemini_api_key", "")
        if not base_url or "dashscope.aliyuncs.com" in base_url:
            base_url = GEMINI_OPENAI_BASE_URL
        if model_brain == "qwen-max":
            model_brain = GEMINI_DEFAULT_MODEL
        if model_vision == "qwen-vl-max":
            model_vision = GEMINI_DEFAULT_MODEL
        if model_chat == "qwen-plus":
            model_chat = GEMINI_DEFAULT_MODEL
    elif provider in {"bailian", "dashscope", "qwen"}:
        provider = "dashscope"
        if not base_url:
            base_url = DASHSCOPE_DEFAULT_BASE_URL
    elif provider in {"agnes", "agnes-ai", "agnes_ai"}:
        provider = "agnes"
        if not base_url:
            base_url = AGNES_DEFAULT_BASE_URL
        if model_brain == "qwen-max":
            model_brain = AGNES_DEFAULT_MODEL
        if model_vision == "qwen-vl-max":
            model_vision = AGNES_DEFAULT_MODEL
        if model_chat == "qwen-plus":
            model_chat = AGNES_DEFAULT_MODEL

    return {
        "provider": provider,
        "api_key": api_key,
        "base_url": base_url or "",
        "model_brain": model_brain,
        "model_vision": model_vision,
        "model_chat": model_chat,
    }


@lru_cache
def get_llm_client() -> LLMClient:
    """
    Get or create the singleton LLM client.
    
    Returns:
        LLMClient: Configured multi-model client instance.
    """
    global _llm_client
    if _llm_client is None:
        settings = get_settings()
        provider_settings = resolve_llm_provider_settings(settings)
        _llm_client = LLMClient(
            api_key=provider_settings["api_key"],
            provider=provider_settings["provider"],
            base_url=provider_settings["base_url"] or None,
            model_brain=provider_settings["model_brain"],
            model_vision=provider_settings["model_vision"],
            model_chat=provider_settings["model_chat"],
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
            sdk_max_retries=settings.llm_sdk_max_retries,
        )
    return _llm_client
