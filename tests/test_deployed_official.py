#!/usr/bin/env python3
"""Test deployed agent using official LangGraph SDK pattern"""
import os
from dotenv import load_dotenv
from langgraph_sdk import get_sync_client

load_dotenv()

# Official setup
DEPLOYMENT_URL = "https://roa-voice-dev-6d8ceb540dee59cebd2fc361aa316dec.us.langgraph.app"
API_KEY = os.getenv("LANGSMITH_API_KEY")
ASSISTANT_ID = "agent"  # From langgraph.json

print(f"🚀 Testing ROA Agent - Official SDK Pattern")
print(f"🔗 Deployment: {DEPLOYMENT_URL}")
print(f"🔑 API Key: {API_KEY[:20]}...")
print()

# Create client
client = get_sync_client(url=DEPLOYMENT_URL, api_key=API_KEY)

def test_recipe_scaling_conversation():
    """Test multi-turn recipe scaling conversation (OFFICIAL PATTERN)"""
    
    # Step 1: Create a thread for conversation
    print("📝 Creating conversation thread...")
    thread = client.threads.create()
    thread_id = thread["thread_id"]
    print(f"✅ Thread created: {thread_id}\n")
    
    # Step 2: Multi-turn conversation
    conversation = [
        "Hello! Can you help me scale a recipe?",
        "I have a pasta recipe that serves 4. Can you help me scale it to serve 8?",
        "The recipe calls for 400g pasta, 2 cups tomato sauce, and 200g cheese. What should I use for 8 people?"
    ]
    
    for i, user_message in enumerate(conversation, 1):
        print(f"\n{'='*80}")
        print(f"👤 User (Turn {i}): {user_message}")
        print(f"{'='*80}")
        
        try:
            # Official streaming pattern
            agent_response = ""
            for chunk in client.runs.stream(
                thread_id,                    # Thread ID (positional arg 1)
                ASSISTANT_ID,                 # Assistant ID (positional arg 2)
                input={                       # Input (keyword arg)
                    "messages": [{
                        "role": "human",
                        "content": user_message
                    }]
                },
                stream_mode="updates"         # Stream mode (keyword arg)
            ):
                # Extract response from updates
                if hasattr(chunk, 'data') and chunk.data:
                    data = chunk.data
                    
                    # Look for message content in various node types
                    for key, value in data.items():
                        if isinstance(value, dict) and "messages" in value:
                            messages = value["messages"]
                            if messages and len(messages) > 0:
                                last_msg = messages[-1]
                                if isinstance(last_msg, dict) and "content" in last_msg:
                                    content = last_msg["content"]
                                    if content and isinstance(content, str) and content.strip():
                                        agent_response = content
            
            if agent_response:
                print(f"\n🤖 Agent: {agent_response}\n")
            else:
                print(f"\n⚠️  Agent responded but no text content extracted\n")
                
        except Exception as e:
            print(f"\n❌ Error: {e}\n")
            import traceback
            traceback.print_exc()
            break
    
    print(f"\n{'='*80}")
    print(f"✅ Conversation test complete!")
    print(f"🔗 View in LangSmith: https://smith.langchain.com/")
    print(f"📊 Thread ID: {thread_id}")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    test_recipe_scaling_conversation()
