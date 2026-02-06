"""
LLM interface package.
LLM 接口包

Provides unified access to large language model APIs and RAG retrieval.
提供大语言模型 API 和 RAG 检索的统一访问接口
"""

from app.llm.client import LLMClient, get_llm_client
from app.llm.tools import AVAILABLE_TOOLS, get_tool_definitions

__all__ = [
    "LLMClient",
    "get_llm_client",
    "AVAILABLE_TOOLS",
    "get_tool_definitions",
]

