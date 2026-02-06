"""
External services verification tests.
外部服务验证测试

Tests LLM API, Ollama Embedding, and ChromaDB connections.
测试 LLM API、Ollama Embedding 和 ChromaDB 连接
"""

import asyncio
import pytest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import get_settings


def print_header(title: str) -> None:
    """Print section header."""
    print("\n" + "=" * 60)
    print(f"🔍 {title}")
    print("=" * 60)


def print_result(name: str, success: bool, message: str = "") -> None:
    """Print test result."""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"  {status} - {name}")
    if message:
        print(f"       {message}")


class TestLLMAPI:
    """Test LLM API connection."""

    @pytest.mark.asyncio
    async def test_chat_completion(self):
        """Test LLM chat API call."""
        print_header("LLM API 验证 (阿里云百炼)")
        
        from app.llm.client import get_llm_client
        
        client = get_llm_client()
        settings = get_settings()
        
        print(f"  配置信息:")
        print(f"    - Base URL: {settings.llm_base_url}")
        print(f"    - Chat Model: {settings.llm_model_chat}")
        print(f"    - API Key: {'*' * 10}...{settings.llm_api_key[-4:] if len(settings.llm_api_key) > 4 else '未配置'}")
        print()
        
        # Test chat completion
        messages = [
            {"role": "user", "content": "请用一句话介绍碳循环饮食法。"}
        ]
        
        response = await client.chat(messages)
        content = response.get("content", "")
        
        print_result("Chat API 调用", bool(content), f"响应: {content[:100]}..." if content else "无响应")
        assert content, "LLM API 返回空响应"


class TestOllamaEmbedding:
    """Test Ollama embedding service."""

    @pytest.mark.asyncio
    async def test_embedding_generation(self):
        """Test Ollama embedding generation."""
        print_header("Ollama Embedding 验证")
        
        from app.rag.embedding import get_embedding_client
        
        client = get_embedding_client()
        settings = get_settings()
        
        print(f"  配置信息:")
        print(f"    - Base URL: {settings.embedding_base_url}")
        print(f"    - Model: {settings.embedding_model}")
        print()
        
        # Test embedding generation
        test_text = "碳循环饮食是一种周期性调整碳水化合物摄入的饮食方法"
        embedding = await client.embed(test_text)
        
        print_result("Embedding 生成", bool(embedding and len(embedding) > 0), 
                    f"向量维度: {len(embedding)}" if embedding else "返回空向量")
        assert embedding and len(embedding) > 0, "Embedding 生成失败"


class TestVectorStore:
    """Test VectorStore connection."""

    @pytest.mark.asyncio
    async def test_vector_store_operations(self):
        """Test add and query operations."""
        print_header("VectorStore (Qdrant) 验证")
        
        from app.rag.vectorstore import get_vector_store
        
        vectorstore = get_vector_store()
        settings = get_settings()
        
        print(f"  配置信息:")
        print(f"    - Persist Dir: {settings.vector_store_persist_dir}")
        print(f"    - Collection: {settings.vector_store_collection_name}")
        print()
        
        # Test add and query
        test_doc = "碳循环饮食通过高碳日、中碳日、低碳日的循环来优化代谢。"
        # Qdrant requires UUID or Int ID. Let the store handle generation or use UUID
        import uuid
        test_id = str(uuid.uuid4())
        
        # Add document
        await vectorstore.add_documents(
            documents=[test_doc],
            ids=[test_id],
            metadatas=[{"source": "verification_test"}]
        )
        print_result("文档添加", True)
        
        # Query document
        results = await vectorstore.query("碳循环饮食原理", n_results=1)
        
        has_results = len(results) > 0
        print_result("向量检索", has_results, f"检索到 {len(results)} 条结果" if has_results else "无结果")
        
        # Cleanup test document
        await vectorstore.delete(ids=[test_id])
        print_result("测试数据清理", True)
        
        assert has_results, "VectorStore 检索失败"


async def run_all_verifications():
    """Run all verifications manually."""
    print("\n" + "🚀 CarbonCycle-FitAgent 外部服务验证" + "\n")
    
    results = []
    
    # 1. LLM API
    try:
        test = TestLLMAPI()
        await test.test_chat_completion()
        results.append(("LLM API", True))
    except Exception as e:
        print(f"  ❌ FAIL - LLM API: {e}")
        results.append(("LLM API", False))
    
    # 2. Ollama Embedding
    try:
        test = TestOllamaEmbedding()
        await test.test_embedding_generation()
        results.append(("Ollama Embedding", True))
    except Exception as e:
        print(f"  ❌ FAIL - Ollama Embedding: {e}")
        results.append(("Ollama Embedding", False))
    
    # 3. VectorStore
    try:
        test = TestVectorStore()
        await test.test_vector_store_operations()
        results.append(("VectorStore", True))
    except Exception as e:
        print(f"  ❌ FAIL - VectorStore: {e}")
        results.append(("VectorStore", False))
    
    # Summary
    print_header("验证结果汇总")
    
    all_passed = True
    for name, passed in results:
        status = "✅" if passed else "❌"
        print(f"  {status} {name}")
        if not passed:
            all_passed = False
    
    print()
    if all_passed:
        print("🎉 所有外部服务验证通过！可以进入下一阶段开发。")
    else:
        print("⚠️ 部分服务验证失败，请检查配置后重试。")
    
    return all_passed


if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    success = asyncio.run(run_all_verifications())
    sys.exit(0 if success else 1)
