"""Quick LLM test."""
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

async def test():
    from app.llm.client import get_llm_client
    llm = get_llm_client()
    
    messages = [
        {"role": "system", "content": "你是一个碳循环饮食规划师。"},
        {"role": "user", "content": "请简单介绍碳循环饮食的原理。"},
    ]
    
    response = await llm.plan(messages)
    content = response.get("content", "")
    
    print("Status: success")
    print(f"Content type: {type(content)}")
    print(f"Content length: {len(content)}")
    print(f"Content: {content[:500]}")

if __name__ == "__main__":
    asyncio.run(test())
