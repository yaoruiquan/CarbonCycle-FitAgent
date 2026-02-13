"""
Hybrid RAG retriever with Unstructured document processing.
混合 RAG 检索器，使用 Unstructured 文档处理

Provides knowledge retrieval for Planner and Actor nodes.
为 Planner 和 Actor 节点提供知识检索

Features:
- Unstructured for intelligent markdown parsing and chunking
- Hybrid search: Vector (semantic) + BM25 (keyword)
"""

import re
import math
from pathlib import Path
from typing import Any, Optional, Union
from collections import defaultdict

from app.core.config import get_settings
from app.core.logging import get_logger
from app.rag.embedding import get_embedding_client
from app.rag.vectorstore import get_vector_store

logger = get_logger(__name__)


# ============================================================
# BM25 Index for Keyword Search
# BM25 索引用于关键词检索
# ============================================================

class BM25Index:
    """
    Simple BM25 index for keyword-based retrieval.
    简单的 BM25 索引用于关键词检索
    """
    
    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self.documents: list[dict[str, Any]] = []
        self.doc_lengths: list[int] = []
        self.avg_doc_length: float = 0
        self.term_doc_freq: dict[str, int] = defaultdict(int)
        self.doc_term_freq: list[dict[str, int]] = []
        
    def _tokenize(self, text: str) -> list[str]:
        """Tokenize Chinese and English text."""
        tokens = []
        # Chinese characters as individual tokens
        chinese = re.findall(r'[\u4e00-\u9fff]+', text)
        for word in chinese:
            tokens.extend(list(word))
        # English words
        english = re.findall(r'[a-zA-Z]+', text.lower())
        tokens.extend(english)
        return tokens
    
    def add_documents(
        self,
        documents: list[str],
        ids: list[str],
        metadatas: Optional[list[dict]] = None,
    ) -> None:
        """Add documents to BM25 index."""
        for i, doc in enumerate(documents):
            tokens = self._tokenize(doc)
            term_freq: dict[str, int] = defaultdict(int)
            
            for token in tokens:
                term_freq[token] += 1
            
            for term in term_freq:
                self.term_doc_freq[term] += 1
            
            self.documents.append({
                "id": ids[i],
                "content": doc,
                "metadata": metadatas[i] if metadatas else {},
            })
            self.doc_lengths.append(len(tokens))
            self.doc_term_freq.append(dict(term_freq))
        
        if self.doc_lengths:
            self.avg_doc_length = sum(self.doc_lengths) / len(self.doc_lengths)
    
    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """Search documents using BM25 scoring."""
        if not self.documents:
            return []
        
        query_tokens = self._tokenize(query)
        n = len(self.documents)
        scores = []
        
        for i, doc in enumerate(self.documents):
            score = 0
            doc_len = self.doc_lengths[i]
            term_freq = self.doc_term_freq[i]
            
            for token in query_tokens:
                if token not in term_freq:
                    continue
                
                tf = term_freq[token]
                df = self.term_doc_freq.get(token, 0)
                
                idf = math.log((n - df + 0.5) / (df + 0.5) + 1)
                tf_norm = (tf * (self.k1 + 1)) / (
                    tf + self.k1 * (1 - self.b + self.b * doc_len / self.avg_doc_length)
                )
                score += idf * tf_norm
            
            scores.append((score, i))
        
        scores.sort(reverse=True)
        
        results = []
        for score, idx in scores[:top_k]:
            if score > 0:
                results.append({
                    "id": self.documents[idx]["id"],
                    "content": self.documents[idx]["content"],
                    "metadata": self.documents[idx]["metadata"],
                    "bm25_score": score,
                })
        
        return results
    
    def clear(self) -> None:
        """Clear all documents from index."""
        self.documents = []
        self.doc_lengths = []
        self.avg_doc_length = 0
        self.term_doc_freq = defaultdict(int)
        self.doc_term_freq = []


# ============================================================
# Document Loader using Unstructured
# 使用 Unstructured 的文档加载器
# ============================================================

def load_markdown_documents(file_path: Union[str, Path]) -> list[dict[str, Any]]:
    """
    Load and parse markdown file using Unstructured.
    使用 Unstructured 加载和解析 Markdown 文件
    
    Args:
        file_path: Path to markdown file.
        
    Returns:
        List of document chunks with content and metadata.
    """
    from unstructured.partition.md import partition_md
    from unstructured.chunking.title import chunk_by_title
    
    file_path = Path(file_path)
    
    # Parse markdown into elements
    elements = partition_md(filename=str(file_path))
    
    # Chunk by title (header-based intelligent chunking)
    chunks = chunk_by_title(
        elements,
        max_characters=800,
        new_after_n_chars=500,
        combine_text_under_n_chars=200,
    )
    
    documents = []
    for i, chunk in enumerate(chunks):
        documents.append({
            "content": str(chunk),
            "metadata": {
                "source": file_path.name,
                "chunk_index": i,
                "element_type": chunk.category if hasattr(chunk, 'category') else "unknown",
            }
        })
    
    logger.info(f"Loaded {len(documents)} chunks from {file_path.name}")
    return documents


def load_knowledge_directory(knowledge_dir: Union[str, Path]) -> list[dict[str, Any]]:
    """
    Load all markdown files from a directory.
    从目录加载所有 Markdown 文件
    
    Args:
        knowledge_dir: Path to knowledge directory.
        
    Returns:
        List of all document chunks.
    """
    knowledge_path = Path(knowledge_dir)
    
    if not knowledge_path.exists():
        logger.warning(f"Knowledge directory not found: {knowledge_dir}")
        return []
    
    all_documents = []
    
    for md_file in knowledge_path.glob("*.md"):
        try:
            docs = load_markdown_documents(md_file)
            all_documents.extend(docs)
        except Exception as e:
            logger.error(f"Failed to load {md_file.name}: {e}")
    
    logger.info(f"Total: {len(all_documents)} chunks from {knowledge_dir}")
    return all_documents


# ============================================================
# Hybrid Retriever
# 混合检索器
# ============================================================

class HybridRetriever:
    """
    Hybrid retriever combining vector search and BM25.
    混合检索器，结合向量检索和 BM25
    """
    
    def __init__(
        self,
        vector_weight: float = 0.7,
        bm25_weight: float = 0.3,
    ) -> None:
        self.vector_weight = vector_weight
        self.bm25_weight = bm25_weight
        self._vector_store = get_vector_store()
        self._bm25_index = BM25Index()
        self._initialized = False
        
        logger.info(
            f"HybridRetriever: vector_weight={vector_weight}, bm25_weight={bm25_weight}"
        )
    
    async def add_documents(
        self,
        documents: list[str],
        ids: Optional[list[str]] = None,
        metadatas: Optional[list[dict]] = None,
    ) -> list[str]:
        """Add documents to both vector store and BM25 index."""
        if not documents:
            return []
        
        # Generate IDs if not provided
        if ids is None:
            from uuid import uuid4
            ids = [str(uuid4()) for _ in documents]
        
        # Add to vector store
        doc_ids = await self._vector_store.add_documents(
            documents=documents,
            ids=ids,
            metadatas=metadatas,
        )
        
        # Add to BM25 index
        self._bm25_index.add_documents(
            documents=documents,
            ids=doc_ids,
            metadatas=metadatas,
        )
        
        logger.info(f"Added {len(documents)} documents to hybrid index")
        return doc_ids
    
    async def search(
        self,
        query: str,
        top_k: int = 5,
        where: Optional[dict] = None,
    ) -> list[dict[str, Any]]:
        """Perform hybrid search combining vector and BM25 results."""
        # Vector search
        vector_results = await self._vector_store.query(
            query_text=query,
            n_results=top_k * 2,
            where=where,
        )
        
        # BM25 search
        bm25_results = self._bm25_index.search(query, top_k=top_k * 2)
        
        # Merge and re-rank
        merged = self._merge_results(vector_results, bm25_results)
        
        logger.debug(
            f"Hybrid search: query='{query[:30]}...', "
            f"vector={len(vector_results)}, bm25={len(bm25_results)}, merged={len(merged)}"
        )
        
        return merged[:top_k]
    
    def _merge_results(
        self,
        vector_results: list[dict],
        bm25_results: list[dict],
    ) -> list[dict[str, Any]]:
        """Merge and re-rank results from both sources."""
        merged: dict[str, dict] = {}
        
        # Process vector results
        if vector_results:
            max_dist = max(r.get("distance", 1) for r in vector_results) or 1
            for r in vector_results:
                doc_id = r["id"]
                vector_score = 1 - (r.get("distance", 0) / max_dist)
                merged[doc_id] = {
                    "id": doc_id,
                    "content": r["content"],
                    "metadata": r.get("metadata", {}),
                    "vector_score": vector_score,
                    "bm25_score": 0,
                }
        
        # Process BM25 results
        if bm25_results:
            max_bm25 = max(r.get("bm25_score", 1) for r in bm25_results) or 1
            for r in bm25_results:
                doc_id = r["id"]
                bm25_score = r.get("bm25_score", 0) / max_bm25
                
                if doc_id in merged:
                    merged[doc_id]["bm25_score"] = bm25_score
                else:
                    merged[doc_id] = {
                        "id": doc_id,
                        "content": r["content"],
                        "metadata": r.get("metadata", {}),
                        "vector_score": 0,
                        "bm25_score": bm25_score,
                    }
        
        # Calculate combined score
        for doc_id in merged:
            merged[doc_id]["combined_score"] = (
                self.vector_weight * merged[doc_id]["vector_score"] +
                self.bm25_weight * merged[doc_id]["bm25_score"]
            )
        
        # Sort by combined score
        results = sorted(
            merged.values(),
            key=lambda x: x["combined_score"],
            reverse=True,
        )
        
        return results


# ============================================================
# Singleton and Helper Functions
# 单例和辅助函数
# ============================================================

_retriever: Optional[HybridRetriever] = None


def get_retriever() -> HybridRetriever:
    """Get or create the singleton hybrid retriever."""
    global _retriever
    if _retriever is None:
        _retriever = HybridRetriever()
    return _retriever


async def load_knowledge_base(knowledge_dir: str = "./data/knowledge") -> int:
    """
    Load markdown files from knowledge directory into retriever.
    
    Uses Unstructured for intelligent document parsing and chunking.
    使用 Unstructured 进行智能文档解析和分块
    
    Args:
        knowledge_dir: Path to knowledge documents directory.
        
    Returns:
        Number of document chunks loaded.
    """
    # Load and chunk documents using Unstructured
    documents = load_knowledge_directory(knowledge_dir)
    
    if not documents:
        return 0
    
    # Prepare for retriever
    contents = [doc["content"] for doc in documents]
    ids = [f"{doc['metadata']['source']}_{doc['metadata']['chunk_index']}" for doc in documents]
    metadatas = [doc["metadata"] for doc in documents]
    
    # Add to retriever
    retriever = get_retriever()
    await retriever.add_documents(
        documents=contents,
        ids=ids,
        metadatas=metadatas,
    )
    
    logger.info(f"Knowledge base loaded: {len(documents)} chunks")
    return len(documents)


async def retrieve_context(query: str, top_k: int = 3) -> str:
    """
    Retrieve relevant context for RAG.
    检索 RAG 相关上下文
    
    Args:
        query: User query or topic.
        top_k: Number of chunks to retrieve.
        
    Returns:
        Concatenated context string.
    """
    retriever = get_retriever()
    results = await retriever.search(query, top_k=top_k)
    
    if not results:
        return ""
    
    context_parts = []
    for r in results:
        source = r.get("metadata", {}).get("source", "unknown")
        content = r.get("content", "")
        context_parts.append(f"[来源: {source}]\n{content}")
    
    return "\n\n---\n\n".join(context_parts)
