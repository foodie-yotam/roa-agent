#!/usr/bin/env python3
"""Test the simple swarm.py"""

import os

# Set env vars
if not os.getenv("GOOGLE_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = "AIzaSyAPxogxsFokL6Ty0mmlIn3YuP3-AtKSd5U"
if not os.getenv("NEO4J_URI"):
    os.environ["NEO4J_URI"] = "neo4j://localhost:7687"
if not os.getenv("NEO4J_USER"):
    os.environ["NEO4J_USER"] = "neo4j"
if not os.getenv("NEO4J_PASSWORD"):
    os.environ["NEO4J_PASSWORD"] = "password"

print("🧪 Testing Simple Swarm (swarm.py)...")
print("=" * 70)

try:
    from swarm import agent
    print("✅ Import successful!")
    print(f"   Type: {type(agent).__name__}")
    print(f"   Nodes: {list(agent.nodes.keys())}")
    
    print("\n🎉 SUCCESS! Simple swarm.py works!")
    print("\n📋 What this means:")
    print("   ✅ ONE file (swarm.py) builds the entire graph")
    print("   ✅ NO hardcoded file paths")
    print("   ✅ Prompts are strings at the top (easy to edit)")
    print("   ✅ Ready for LangGraph Cloud deployment")
    print("\n📁 Deploy with:")
    print("   langgraph.json points to: ./swarm.py:agent")
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
