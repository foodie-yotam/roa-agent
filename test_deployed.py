#!/usr/bin/env python3
"""Test the deployed agent on LangGraph Cloud"""
import os
import uuid
from dotenv import load_dotenv
from langgraph_sdk import get_sync_client

load_dotenv()

# Connect to roa-voice-dev deployment (from screenshot)
# Deployment ID: dae06188-c625-4e67-9885-cc30453a0d1e
LANGGRAPH_URL = "https://roa-voice-dev-6d8ceb540dee59cebd2fc361aa316dec.us.langgraph.app"
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")

print(f"🚀 Testing ROA Voice Agent - Dev Deployment")
print(f"🔗 URL: {LANGGRAPH_URL}")
print(f"🔑 API Key: {LANGSMITH_API_KEY[:20]}..." if LANGSMITH_API_KEY else "❌ No API key found")
print()

client = get_sync_client(url=LANGGRAPH_URL, api_key=LANGSMITH_API_KEY)

def test_conversation(messages):
    """Test a conversation with the deployed agent"""
    # Simple thread ID (similar to Flask server pattern)
    thread_id = str(uuid.uuid4())
    
    print(f"\n{'='*80}")
    print(f"🆔 Thread: {thread_id}")
    print(f"{'='*80}\n")
    
    for i, msg in enumerate(messages, 1):
        print(f"\n👤 User (message {i}): {msg}")
        print("-" * 80)
        
        try:
            # Send message to agent (same pattern as Flask server)
            input_data = {"messages": [{"role": "user", "content": msg}]}
            
            # Stream response
            response_text = ""
            for chunk in client.runs.stream(
                thread_id,
                assistant_id="agent",
                input=input_data,
                stream_mode="updates"
            ):
                if hasattr(chunk, 'data') and chunk.data:
                    # Extract response from updates
                    for key, value in chunk.data.items():
                        if isinstance(value, dict) and "messages" in value:
                            msgs = value["messages"]
                            if msgs and len(msgs) > 0:
                                last_msg = msgs[-1]
                                if isinstance(last_msg, dict) and "content" in last_msg:
                                    content = last_msg.get("content", "")
                                    if content and isinstance(content, str):
                                        response_text = content
            
            if response_text:
                print(f"\n🤖 Agent: {response_text}\n")
            else:
                print(f"\n🤖 Agent: [No text response extracted]\n")
                
        except Exception as e:
            print(f"\n❌ Error: {e}\n")
            import traceback
            traceback.print_exc()
            break
    
    print(f"\n{'='*80}")
    print(f"✅ Conversation complete!")
    print(f"View in LangSmith: https://smith.langchain.com/")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    # Test: Simple recipe scaling conversation
    test_conversation([
        "Hello! Can you help me scale a recipe?",
        "I have a pasta recipe that serves 4. Can you help me scale it to serve 8?",
        "The recipe calls for 400g pasta, 2 cups tomato sauce, and 200g cheese. What should I use for 8 people?"
    ])
