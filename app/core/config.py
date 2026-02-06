"""
Application configuration management.
应用程序配置管理

Uses Pydantic Settings for environment variable parsing and validation.
使用 Pydantic Settings 进行环境变量解析和验证
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    Supports multi-model LLM configuration:
    - Brain (Qwen-Max): Complex planning and reasoning
    - Vision (Qwen-VL-Max): Image recognition, OCR
    - Chat (Qwen-Plus): Daily conversation, text generation
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    # Application
    app_name: str = "CarbonCycle-FitAgent"
    app_version: str = "0.1.0"
    debug: bool = False
    
    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    
    # Database
    database_url: str = "sqlite+aiosqlite:///./data/carboncycle.db"
    
    # LLM Configuration - Aliyun Bailian API
    llm_api_key: str = ""
    llm_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    llm_temperature: float = 0.7
    llm_max_tokens: int = 4096
    
    # Multi-Model Configuration
    llm_model_brain: str = "qwen-max"          # Complex planning, reasoning
    llm_model_vision: str = "qwen-vl-max"      # Image understanding, OCR
    llm_model_chat: str = "qwen-plus"          # Daily chat, text polish
    
    # Embedding Configuration - Ollama + BGE-M3
    embedding_model: str = "bge-m3"
    embedding_base_url: str = "http://localhost:11434"
    embedding_dimension: int = 1024
    
    # Vector Database - Qdrant
    vector_store_persist_dir: str = "./data/qdrant"
    vector_store_collection_name: str = "carboncycle_knowledge"
    
    # Agent Configuration
    agent_max_iterations: int = 10
    agent_reflection_threshold: float = 0.2  # 20% deviation triggers reflection


@lru_cache
def get_settings() -> Settings:
    """
    Get cached application settings instance.
    
    Returns:
        Settings: Singleton settings object.
    """
    return Settings()
