"""
Embedding client using Ollama + BGE-M3.
使用 Ollama + BGE-M3 的嵌入客户端

Provides text embedding for RAG and semantic search.
为 RAG 和语义搜索提供文本嵌入
"""

from typing import Optional

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class EmbeddingClient:
    """
    Embedding client using Ollama with BGE-M3 model.
    
    BGE-M3 is a multi-lingual, multi-granularity embedding model
    that excels at both dense and sparse retrieval.
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "bge-m3",
        dimension: int = 1024,
    ) -> None:
        """
        Initialize embedding client.
        
        Args:
            base_url: Ollama server URL.
            model: Embedding model name.
            dimension: Embedding vector dimension.
        """
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.dimension = dimension
        self._timeout = httpx.Timeout(60.0, connect=10.0)
    
    async def embed(self, text: str) -> list[float]:
        """
        Generate embedding for single text.
        
        Args:
            text: Input text to embed.
            
        Returns:
            Embedding vector as list of floats.
        """
        url = f"{self.base_url}/api/embeddings"
        payload = {
            "model": self.model,
            "prompt": text,
        }
        
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                
                embedding = data.get("embedding", [])
                return embedding
            
        except httpx.HTTPError as e:
            logger.error(f"Embedding API error: {e}")
            raise
    
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed.
            
        Returns:
            List of embedding vectors.
        """
        embeddings = []
        for text in texts:
            emb = await self.embed(text)
            embeddings.append(emb)
        return embeddings


# Singleton instance
_embedding_client: Optional[EmbeddingClient] = None


def get_embedding_client() -> EmbeddingClient:
    """
    Get or create the singleton embedding client.
    
    Returns:
        EmbeddingClient: Configured client instance.
    """
    global _embedding_client
    if _embedding_client is None:
        settings = get_settings()
        _embedding_client = EmbeddingClient(
            base_url=settings.embedding_base_url,
            model=settings.embedding_model,
            dimension=settings.embedding_dimension,
        )
    return _embedding_client
