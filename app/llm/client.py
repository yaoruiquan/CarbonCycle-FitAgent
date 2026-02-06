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
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from openai import AsyncOpenAI

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


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
        base_url: Optional[str] = None,
        model_brain: str = "qwen-max",
        model_vision: str = "qwen-vl-max",
        model_chat: str = "qwen-plus",
        temperature: float = 0.7,
        max_tokens: int = 4096,
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
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
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
        tool_choice: Optional[str | dict[str, Any]] = None,
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
            logger.error(f"LLM API error: {e}")
            raise
    
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
        image_path: str | Path,
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
            logger.error(f"LLM stream error: {e}")
            raise


# Singleton client instance
_llm_client: Optional[LLMClient] = None


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
        _llm_client = LLMClient(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url or None,
            model_brain=settings.llm_model_brain,
            model_vision=settings.llm_model_vision,
            model_chat=settings.llm_model_chat,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
        )
    return _llm_client
