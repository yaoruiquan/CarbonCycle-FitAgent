"""
Knowledge base initialization and RAG test script.
知识库初始化和 RAG 测试脚本

Uses Unstructured for document processing.
使用 Unstructured 进行文档处理
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


async def test_rag():
    """Test RAG with Unstructured document loading."""
    print("=" * 60)
    print("[1/3] Loading Documents with Unstructured")
    print("=" * 60)
    
    from app.rag.retriever import load_knowledge_directory
    
    # Test document loading
    docs = load_knowledge_directory("./data/knowledge")
    print(f"Loaded {len(docs)} document chunks")
    
    if docs:
        print("\nSample chunks:")
        for i, doc in enumerate(docs[:3]):
            source = doc["metadata"]["source"]
            content = doc["content"][:100].replace("\n", " ")
            print(f"  [{i+1}] {source}: {content}...")
    
    print("\n" + "=" * 60)
    print("[2/3] Initializing Hybrid Retriever")
    print("=" * 60)
    
    from app.rag.retriever import load_knowledge_base
    
    num_chunks = await load_knowledge_base("./data/knowledge")
    print(f"Indexed {num_chunks} chunks in hybrid retriever")
    
    print("\n" + "=" * 60)
    print("[3/3] Testing Hybrid Search")
    print("=" * 60)
    
    from app.rag.retriever import get_retriever, retrieve_context, load_knowledge_directory
    
    retriever = get_retriever()
    
    test_queries = [
        "什么是碳循环饮食",
        "如何计算TDEE",
        "高碳日吃什么",
        "低碳日宏量比例",
    ]
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        print("-" * 40)
        
        results = await retriever.search(query, top_k=2)
        
        for i, r in enumerate(results):
            score = r.get("combined_score", 0)
            v_score = r.get("vector_score", 0)
            b_score = r.get("bm25_score", 0)
            source = r.get("metadata", {}).get("source", "?")
            content = r.get("content", "")[:80].replace("\n", " ")
            
            print(f"  [{i+1}] Score: {score:.3f} (V:{v_score:.2f} B:{b_score:.2f})")
            print(f"      Source: {source}")
            print(f"      Content: {content}...")
    
    # Test context retrieval helper
    print("\n" + "=" * 60)
    print("[Bonus] retrieve_context() Helper")
    print("=" * 60)
    
    context = await retrieve_context("碳循环饮食的核心原理是什么", top_k=2)
    print(f"Context length: {len(context)} chars")
    print(f"Preview: {context[:200]}...")
    
    print("\n" + "=" * 60)
    print("[OK] RAG System Ready!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_rag())
