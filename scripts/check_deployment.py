#!/usr/bin/env python3
"""Check what's deployed on LangGraph Cloud"""
import os
from dotenv import load_dotenv
from langgraph_sdk import get_sync_client

load_dotenv()

LANGGRAPH_URL = "https://roa-voice-dev-6d8ceb540dee59cebd2fc361aa316dec.us.langgraph.app"
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")

print(f"🔗 Checking deployment: {LANGGRAPH_URL}")
print(f"🔑 API Key: {LANGSMITH_API_KEY[:20]}...")
print()

client = get_sync_client(url=LANGGRAPH_URL, api_key=LANGSMITH_API_KEY)

try:
    # Try to get specific assistant
    print("🔍 Checking 'agent' assistant:")
    try:
        agent_info = client.assistants.get("agent")
        print(f"✅ Found 'agent' assistant!")
        print(f"Details: {agent_info}")
    except Exception as e:
        print(f"❌ Not found: {e}")
    
    print()
    
    # Try to search for assistants
    print("📋 Searching for assistants:")
    try:
        result = client.assistants.search()
        print(f"Found: {result}")
    except Exception as e:
        print(f"Search not available: {e}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
