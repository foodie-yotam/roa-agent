# ROA Agent - Refactored Structure

## Architecture

Hierarchical multi-agent system with proper code organization:
- **Teams = Folders**
- **Agents = Files**
- **Tools shown individually** in LangSmith traces

## Structure

```
agent/
├── src/                       # Source code
│   ├── shared/               # Shared utilities
│   │   ├── state.py         # State definition
│   │   ├── supervisor.py    # Supervisor routing logic
│   │   └── db.py            # Neo4j connection
│   │
│   └── teams/               # Team hierarchies
│       ├── chef/            # Chef meta-team
│       │   ├── kitchen/     # Kitchen subteam (recipes, team, dishes)
│       │   ├── inventory/   # Inventory subteam (stock, suppliers, forecasts)
│       │   └── sales/       # Sales subteam (cost analysis)
│       │
│       ├── builder/         # Builder team (dev tools)
│       ├── visualization/   # Visualization team (React Flow displays)
│       └── marketing/       # Marketing team (content generation)
│
├── agent.py                  # Root graph orchestration (MAIN FILE)
├── langgraph.json           # LangGraph Cloud config
├── requirements.txt         # Python dependencies
│
├── scripts/                 # Debug & analysis scripts
│   ├── query_hierarchy.py   # LangSmith trace analysis (MOST USEFUL)
│   ├── query_langsmith.py   # Basic run queries
│   └── check_deployment.py  # Deployment status
│
├── tests/                   # Test suite
│   ├── test_local.py        # Local testing
│   ├── test_deployed.py     # Deployment testing
│   └── test_neo4j.py        # Database testing
│
├── ROA-CONVOS/             # Conversation logs & analysis
│   ├── hierarchy_*.txt      # Full trace hierarchies
│   └── ANALYSIS.md          # Bug analysis & findings
│
└── trash/                   # Deprecated files (safe to delete)
```

## Key Features

### Individual Tool Nodes
Instead of bundling tools into a single "tools" node, each tool is a separate node:

```python
# OLD (create_react_agent) - bundled "tools" node
voice_agent = create_react_agent(llm, [tool1, tool2])

# NEW - individual tool nodes
builder.add_node("tool1", ToolNode([tool1]))
builder.add_node("tool2", ToolNode([tool2]))
```

**Result:** Each tool shows up as a separate node in LangSmith graph visualization! 🎯

### Hierarchical Teams
- **Root Supervisor** → Routes to speaker/chef/builder teams
- **Team Supervisors** → Route to specialized agents
- **Agents** → Call individual tools

### Improved Supervisor Prompts
Supervisors now have clear completion criteria to prevent infinite loops:
- "Each worker should only be called ONCE per task"
- "If worker just responded, task is likely complete"
- "Respond with FINISH if done"

## Running Locally

```bash
# Test with LangSmith tracing
cd /home/yotambg/Documents/foodie-stuff/roa-voice/agent
python3 test_local.py
```

View traces at: https://smith.langchain.com/ → Project: roa-voice-local

## Deployment

Deploy to LangGraph Cloud:
```bash
# Point to new structure
langgraph.json → graphs: "./src/agent.py:agent"
```

## Status

✅ **Implemented:**
- Speaker team (voice, video, marketing)
- Individual tool nodes
- Improved supervisor prompts
- Proper file organization

⏳ **TODO:**
- Complete chef team (kitchen, inventory, sales)
- Builder team
- Recipe tools integration with Neo4j
