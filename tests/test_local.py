#!/usr/bin/env python3
"""Test agent locally with LangSmith tracing"""
import os
from dotenv import load_dotenv
load_dotenv()

# Enable LangSmith tracing
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = "roa-voice-local"
os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"

from src.agent import agent

def test_agent(message: str):
    """Test the agent with a message"""
    print(f"\n{'='*80}")
    print(f"Testing: {message}")
    print(f"{'='*80}\n")
    
    config = {
        "configurable": {"thread_id": "test-thread-1"},
        "recursion_limit": 100
    }
    input_data = {"messages": [{"role": "user", "content": message}]}
    
    for chunk in agent.stream(input_data, config, stream_mode="updates"):
        if chunk:
            for key, value in chunk.items():
                print(f"📦 {key}: {value.get('next', 'processing...')}")
    
    print(f"\n{'='*80}")
    print(f"✅ Complete! View trace in LangSmith:")
    print(f"https://smith.langchain.com/")
    print(f"Project: roa-voice-local")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    # Test 1: Voice
    test_agent("Generate a professional welcome message")
    
    # Test 2: Video visualization  
    test_agent("Show me pasta recipes as a visual")
    
    # Test 3: Marketing
    test_agent("Create marketing content for our seasonal menu")
