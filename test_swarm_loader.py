#!/usr/bin/env python3
"""
Test script to verify swarm_loader works correctly
"""

import os
import sys

# Set environment variables for testing
if not os.getenv("GOOGLE_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = "AIzaSyAPxogxsFokL6Ty0mmlIn3YuP3-AtKSd5U"

# Set dummy Neo4j vars for testing (swarm_loader will override with real ones)
if not os.getenv("NEO4J_URI"):
    os.environ["NEO4J_URI"] = "neo4j://localhost:7687"
if not os.getenv("NEO4J_USER"):
    os.environ["NEO4J_USER"] = "neo4j"
if not os.getenv("NEO4J_PASSWORD"):
    os.environ["NEO4J_PASSWORD"] = "password"

print("🧪 Testing Swarm Loader...")
print("=" * 70)

try:
    from swarm_loader import load_swarm
    print("✅ Import successful")
    
    print("\n📦 Loading swarm from YAML...")
    agent = load_swarm("swarm_config/swarm.yaml")
    
    print("\n✅ Swarm loaded successfully!")
    print(f"   Type: {type(agent)}")
    print(f"   Nodes: {list(agent.nodes.keys()) if hasattr(agent, 'nodes') else 'N/A'}")
    
    print("\n🎉 SUCCESS! Swarm-as-Code is working!")
    print("\n📋 Next steps:")
    print("   1. Replace agent.py with:")
    print("      from swarm_loader import load_swarm")
    print("      agent = load_swarm()")
    print("   2. All prompts will load from .md files")
    print("   3. All configs will load from .yaml files")
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    print(f"\n🐛 Debug info:")
    import traceback
    traceback.print_exc()
    print("\n💡 This helps identify what needs fixing!")
    sys.exit(1)
