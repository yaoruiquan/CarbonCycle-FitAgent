"""
Vector store using Qdrant.
使用 Qdrant 的向量存储（本地文件模式或内存模式）

Replacing ChromaDB for better stability and scalability.
替代 ChromaDB 以获得更好的稳定性和可扩展性。
"""

import uuid
from typing import Any, Optional

from qdrant_client import QdrantClient
from qdrant_client.http import models as rest
from qdrant_client.models import Distance, VectorParams, PointStruct

from app.core.config import get_settings
from app.core.logging import get_logger
from app.rag.embedding import get_embedding_client

logger = get_logger(__name__)


class VectorStore:
    """
    Vector store using Qdrant for knowledge retrieval.
    """
    
    def __init__(
        self,
        persist_dir: str = "./data/qdrant",
        collection_name: str = "carboncycle_knowledge",
    ) -> None:
        """
        Initialize Qdrant vector store.
        
        Args:
            persist_dir: Path for local storage.
            collection_name: Name of the collection.
        """
        self.collection_name = collection_name
        self.vector_size = 1024  # BGE-M3 dimension
        
        # Initialize Qdrant Client (Local persistence)
        # 即使目录不存在，Qdrant 也会自动创建
        self._client = QdrantClient(path=persist_dir)
        
        # Check if collection exists, if not create it
        self._ensure_collection_exists()
        
        self._embedding_client = get_embedding_client()
        
        logger.info(
            f"VectorStore (Qdrant) initialized: collection={collection_name}"
        )
    
    def _ensure_collection_exists(self) -> None:
        """Create collection if not exists."""
        collections = self._client.get_collections().collections
        exists = any(c.name == self.collection_name for c in collections)
        
        if not exists:
            logger.info(f"Creating collection: {self.collection_name}")
            self._client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size,
                    distance=Distance.COSINE
                ),
            )
    
    async def add_documents(
        self,
        documents: list[str],
        ids: Optional[list[str]] = None,
        metadatas: Optional[list[dict[str, Any]]] = None,
    ) -> list[str]:
        """Add documents to Qdrant."""
        if not documents:
            return []
            
        if metadatas is None:
            metadatas = [{} for _ in documents]

        if ids is None:
            ids = [str(uuid.uuid4()) for _ in documents]
        else:
            # Check if IDs are valid UUIDs, if not, map them to UUIDs and store original in metadata
            new_ids = []
            for i, original_id in enumerate(ids):
                try:
                    uuid.UUID(original_id)
                    new_ids.append(original_id)
                except ValueError:
                    # Not a UUID, generate one and store original
                    new_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, original_id))
                    new_ids.append(new_uuid)
                    # We can safely access metadatas[i] because we initialized it above
                    metadatas[i]["_original_id"] = original_id
            ids = new_ids
            
        # Generate embeddings
        embeddings = await self._embedding_client.embed_batch(documents)
        
        # Prepare points
        points = []
        for i in range(len(documents)):
            # Qdrant payload stores content and metadata
            payload = metadatas[i].copy() if metadatas[i] else {}
            payload["content"] = documents[i]
            
            points.append(PointStruct(
                id=ids[i],
                vector=embeddings[i],
                payload=payload
            ))
            
        # Upsert
        self._client.upsert(
            collection_name=self.collection_name,
            points=points
        )
        
        logger.info(f"Added {len(documents)} documents to Qdrant")
        return ids

    async def query(
        self,
        query_text: str,
        n_results: int = 5,
        where: Optional[dict[str, Any]] = None,
    ) -> list[dict[str, Any]]:
        """Query Qdrant."""
        # Generate query embedding
        query_vector = await self._embedding_client.embed(query_text)
        
        # Build filter if provided
        query_filter = None
        if where:
            must_conditions = []
            for k, v in where.items():
                must_conditions.append(
                    rest.FieldCondition(
                        key=k,
                        match=rest.MatchValue(value=v)
                    )
                )
            query_filter = rest.Filter(must=must_conditions)
        
        # Search
        search_result = self._client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            query_filter=query_filter,
            limit=n_results,
            with_payload=True,
        )
        
        # Format results
        documents = []
        for hit in search_result:
            payload = hit.payload or {}
            content = payload.pop("content", "")
            
            documents.append({
                "id": str(hit.id),
                "content": content,
                "metadata": payload,
                "distance": 1.0 - hit.score, # Qdrant cosine is similarity (high is better)
                "score": hit.score, 
            })
            
        return documents

    def count(self) -> int:
        """Count points in collection."""
        info = self._client.get_collection(self.collection_name)
        return info.points_count if info.points_count is not None else 0
        
    async def delete(self, ids: list[str]) -> None:
        """Delete points by IDs."""
        self._client.delete(
            collection_name=self.collection_name,
            points_selector=rest.PointIdsList(points=ids),
        )
        logger.info(f"Deleted {len(ids)} documents")


# Singleton instance
_vector_store: Optional[VectorStore] = None

def get_vector_store() -> VectorStore:
    global _vector_store
    if _vector_store is None:
        settings = get_settings()
        _vector_store = VectorStore(
            persist_dir=settings.vector_store_persist_dir,
            collection_name=settings.vector_store_collection_name,
        )
    return _vector_store
