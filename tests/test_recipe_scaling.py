#!/usr/bin/env python3
"""Test recipe scaling conversation locally with detailed traces"""
import os
from dotenv import load_dotenv
load_dotenv()

# Enable LangSmith tracing for detailed inspection
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = "roa-voice-recipe-scaling"
os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"

# Import the agent from root agent.py (as specified in langgraph.json)
from agent import agent

def test_recipe_scaling():
    """Test a recipe scaling conversation with detailed output"""
    
    conversation = [
        "Hello! Can you help me scale a recipe?",
        "I have a pasta recipe that serves 4. Can you help me scale it to serve 8?",
        "The recipe calls for 400g pasta, 2 cups tomato sauce, and 200g cheese. What should I use for 8 people?"
    ]
    
    config = {
        "configurable": {"thread_id": "recipe-scaling-test"},
        "recursion_limit": 100
    }
    
    for turn, user_message in enumerate(conversation, 1):
        print(f"\n{'='*80}")
        print(f"🔄 TURN {turn}")
        print(f"{'='*80}")
        print(f"👤 User: {user_message}\n")
        
        input_data = {"messages": [{"role": "user", "content": user_message}]}
        
        print("📊 Agent execution trace:")
        print("-" * 80)
        
        try:
            agent_response = None
            for chunk in agent.stream(input_data, config, stream_mode="updates"):
                if chunk:
                    for node_name, node_output in chunk.items():
                        print(f"\n🔹 Node: {node_name}")
                        
                        # Print next routing decision
                        if "next" in node_output:
                            print(f"   ➡️  Next: {node_output['next']}")
                        
                        # Extract messages
                        if "messages" in node_output:
                            messages = node_output["messages"]
                            if messages:
                                for msg in messages:
                                    if isinstance(msg, dict):
                                        role = msg.get("role", msg.get("type", "unknown"))
                                        content = msg.get("content", "")
                                        if content:
                                            print(f"   💬 {role}: {content[:100]}{'...' if len(content) > 100 else ''}")
                                            if role in ["assistant", "ai"]:
                                                agent_response = content
            
            print("-" * 80)
            if agent_response:
                print(f"\n🤖 Agent final response:\n{agent_response}\n")
            else:
                print(f"\n⚠️  No agent response extracted\n")
                
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
            break
    
    print(f"\n{'='*80}")
    print(f"✅ Test complete!")
    print(f"🔗 View detailed trace in LangSmith:")
    print(f"   https://smith.langchain.com/")
    print(f"   Project: roa-voice-recipe-scaling")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    test_recipe_scaling()
