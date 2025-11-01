# 🏗️ Composable Agent Patterns - How to Organize LangGraph Swarms

**Research Date:** 2025-11-02  
**Sources:** LangGraph docs, production codebases, architectural patterns

---

## 🎯 **KEY INSIGHT: No Magic Library - Just Patterns**

**Bad news:** There's no npm/pip package that "just fixes" swarm organization.  
**Good news:** Industry has converged on proven patterns.

**Recommendation for ROA:** Apply these 3 patterns (no new dependencies needed!)

---

## 📊 **PATTERN #1: Official LangGraph Structure** (from LangChain docs)

### **What LangGraph Recommends:**

```
my-app/
├── my_agent/              # All code here
│   ├── utils/
│   │   ├── tools.py       # ← All tools in one place
│   │   ├── nodes.py       # ← All node functions
│   │   └── state.py       # ← State definition
│   ├── __init__.py
│   └── agent.py           # ← Graph construction
├── .env
├── requirements.txt
└── langgraph.json         # ← LangGraph config
```

### **Key Principles:**
1. **Separate tools from nodes from state**
2. **One agent.py constructs the graph**
3. **Utils folder for reusables**

**Problem for ROA:** You have MULTIPLE agents, not one. This is for single-agent apps.

---

## 📊 **PATTERN #2: Modular Multi-Agent Structure** (from production codebases)

### **Industry Standard for Multi-Agent:**

```
roa-agent/
├── agents/                         # ← Agent definitions
│   ├── base_agent.py               # ← Base class
│   ├── factory.py                  # ← Factory functions
│   └── teams/
│       ├── kitchen/
│       │   ├── recipe_agent.py     # One file per agent
│       │   ├── team_pm_agent.py
│       │   └── __init__.py
│       ├── inventory/
│       │   ├── stock_agent.py
│       │   └── __init__.py
│       └── __init__.py
│
├── tools/                          # ← All tools (shared registry)
│   ├── registry.py                 # ← TOOL_REGISTRY
│   ├── recipe_tools.py
│   ├── team_tools.py
│   └── __init__.py
│
├── graphs/                         # ← Graph builders (composable!)
│   ├── base_graph.py               # ← Shared graph logic
│   ├── kitchen_graph.py            # One graph per team
│   ├── inventory_graph.py
│   └── root_graph.py
│
├── state/                          # ← State management
│   ├── base_state.py
│   └── team_states.py
│
├── config/                         # ← Configuration
│   ├── settings.py
│   └── agents.yaml                 # ← Agent registry
│
├── utils/                          # ← Shared utilities
│   ├── circuit_breaker.py
│   ├── evaluator.py
│   └── node_factory.py             # ← Factory for nodes
│
└── agent.py                        # ← Main entry (orchestrates)
```

### **Key Benefits:**
- ✅ **Each agent in own file** (not 1285-line monolith)
- ✅ **Tools in registry** (single source of truth)
- ✅ **Graphs are composable** (import kitchen_graph into chef_graph)
- ✅ **Testable** (test kitchen_graph in isolation)

---

## 📊 **PATTERN #3: Pipeline of Agents** (composable subgraphs)

### **Core Idea: Graphs as Building Blocks**

**Instead of:**
```python
# One giant graph with 50 nodes
root_graph.add_node("recipe")
root_graph.add_node("team_pm")
root_graph.add_node("stock")
# ... 47 more nodes
```

**Do this:**
```python
# Small graphs that compose
kitchen_graph = build_kitchen_graph()   # 3 nodes
inventory_graph = build_inventory_graph()  # 3 nodes
chef_graph = build_chef_graph(kitchen_graph, inventory_graph)  # Composes!
root_graph = build_root_graph(chef_graph, viz_graph, ...)
```

### **Implementation:**

```python
# graphs/kitchen_graph.py
def build_kitchen_graph():
    """Small, testable, composable graph"""
    builder = StateGraph(State)
    builder.add_node("supervisor", kitchen_supervisor)
    builder.add_node("recipe", recipe_node)
    builder.add_node("team_pm", team_pm_node)
    builder.add_edge(START, "supervisor")
    return builder.compile()

# graphs/chef_graph.py
def build_chef_graph(kitchen_graph, inventory_graph, sales_graph):
    """Composes smaller graphs"""
    builder = StateGraph(State)
    builder.add_node("supervisor", chef_supervisor)
    builder.add_node("kitchen_team", kitchen_graph)  # ← Subgraph!
    builder.add_node("inventory_team", inventory_graph)
    builder.add_node("sales_team", sales_graph)
    builder.add_edge(START, "supervisor")
    return builder.compile()
```

**Benefits:**
- ✅ **Test each graph in isolation**
- ✅ **Swap implementations** (mock kitchen_graph for testing)
- ✅ **Clear dependencies** (chef needs kitchen + inventory)
- ✅ **Reusable** (kitchen_graph used in multiple places)

---

## 🎯 **RECOMMENDED REFACTORING FOR ROA**

### **Phase 1: Extract Tools (30 min)**

**Create:** `tools/registry.py`
```python
"""Single source of truth for all tools"""
from .recipe_tools import search_recipes, get_recipe_details
from .team_tools import get_team_members, assign_task
# ... etc

TOOL_REGISTRY = {
    "recipe": [search_recipes, get_recipe_details],
    "team_pm": [get_team_members, assign_task],
    "dish_ideation": [suggest_dishes],
    "stock": [check_stock],
    "suppliers": [list_suppliers],
    "analysis": [forecast_demand],
    "profit": [calculate_cost],
    "visualization": [display_recipes, display_multiplication, ...],
    "marketing": [create_marketing_content],
    "dev_tools": [generate_tool_code],
}
```

**Usage everywhere:**
```python
from tools.registry import TOOL_REGISTRY

# Create agent
recipe_agent = create_react_agent(llm, TOOL_REGISTRY["recipe"], ...)

# Pass to supervisor
kitchen_supervisor = make_supervisor_node(llm, [...], worker_tools={
    name: TOOL_REGISTRY[name] for name in ["recipe", "team_pm", "dish_ideation"]
})
```

---

### **Phase 2: Factory Pattern for Nodes (1 hour)**

**Create:** `utils/node_factory.py`
```python
"""Factory functions for common patterns"""

def create_worker_node(name: str, agent):
    """Factory: Creates node wrapper for any worker agent"""
    def node(state: State) -> Command[Literal["supervisor"]]:
        result = agent.invoke(state)
        return Command(
            update={"messages": [HumanMessage(
                content=result["messages"][-1].content,
                name=name
            )]},
            goto="supervisor"
        )
    return node

def create_team_caller(name: str, team_graph):
    """Factory: Creates caller for a compiled team graph"""
    def caller(state: State) -> Command[Literal["supervisor"]]:
        response = team_graph.invoke({"messages": state["messages"]})
        return Command(
            update={"messages": [HumanMessage(
                content=response["messages"][-1].content,
                name=name
            )]},
            goto="supervisor"
        )
    return caller
```

**Usage:**
```python
from utils.node_factory import create_worker_node, create_team_caller

# Instead of 13 identical functions:
recipe_node = create_worker_node("recipe", recipe_agent)
team_pm_node = create_worker_node("team_pm", team_pm_agent)
# ... etc (1 line each!)

# For team callers:
call_kitchen_team = create_team_caller("kitchen_team", kitchen_team_graph)
```

**Savings:** 156 lines → 15 lines

---

### **Phase 3: Composable Graph Builders (2 hours)**

**Create:** `graphs/kitchen_graph.py`
```python
"""Kitchen team graph - small, testable, composable"""
from tools.registry import TOOL_REGISTRY
from utils.node_factory import create_worker_node

def build_kitchen_graph(llm):
    """Build kitchen team graph (can be tested in isolation!)"""
    # Create agents
    recipe_agent = create_react_agent(llm, TOOL_REGISTRY["recipe"], ...)
    team_pm_agent = create_react_agent(llm, TOOL_REGISTRY["team_pm"], ...)
    dish_agent = create_react_agent(llm, TOOL_REGISTRY["dish_ideation"], ...)
    
    # Create supervisor
    supervisor = make_supervisor_node(
        llm,
        ["recipe", "team_pm", "dish_ideation"],
        worker_tools={
            name: TOOL_REGISTRY[name]
            for name in ["recipe", "team_pm", "dish_ideation"]
        }
    )
    
    # Build graph
    builder = StateGraph(State)
    builder.add_node("supervisor", supervisor)
    builder.add_node("recipe", create_worker_node("recipe", recipe_agent))
    builder.add_node("team_pm", create_worker_node("team_pm", team_pm_agent))
    builder.add_node("dish_ideation", create_worker_node("dish_ideation", dish_agent))
    builder.add_edge(START, "supervisor")
    
    return builder.compile()
```

**Create:** `graphs/chef_graph.py`
```python
"""Chef meta-team graph - composes kitchen + inventory + sales"""
from .kitchen_graph import build_kitchen_graph
from .inventory_graph import build_inventory_graph
from .sales_graph import build_sales_graph

def build_chef_graph(llm):
    """Compose smaller graphs into chef team"""
    # Build subgraphs
    kitchen_graph = build_kitchen_graph(llm)
    inventory_graph = build_inventory_graph(llm)
    sales_graph = build_sales_graph(llm)
    
    # Create supervisor (sees abstract descriptions!)
    supervisor = make_supervisor_node(
        llm,
        ["kitchen_team", "inventory_team", "sales_team"],
        worker_tools={
            "kitchen_team": "Manages recipes, team, and dishes",
            "inventory_team": "Tracks stock and suppliers",
            "sales_team": "Analyzes costs and profitability"
        }
    )
    
    # Build graph
    builder = StateGraph(State)
    builder.add_node("supervisor", supervisor)
    builder.add_node("kitchen_team", kitchen_graph)  # ← Subgraph!
    builder.add_node("inventory_team", inventory_graph)
    builder.add_node("sales_team", sales_graph)
    builder.add_edge(START, "supervisor")
    
    return builder.compile()
```

**Main `agent.py` becomes:**
```python
"""Main agent orchestration - now just 50 lines!"""
from graphs.chef_graph import build_chef_graph
from graphs.viz_graph import build_viz_agent
# ... etc

llm = ChatGoogleGenerativeAI(...)

# Build composed graph
chef_graph = build_chef_graph(llm)
viz_agent = build_viz_agent(llm)
# ... etc

# Root just composes
root_builder = StateGraph(State)
root_builder.add_node("chef_team", chef_graph)
root_builder.add_node("visualization", viz_agent)
# ... etc

agent = root_builder.compile()
```

---

## 📚 **TESTING BENEFITS**

### **Before (Monolith):**
```python
# Can only test the WHOLE system
def test_recipe_lookup():
    result = agent.invoke({"messages": [...]})
    # Runs through: root → chef → kitchen → recipe
    # If it fails, where's the bug?
```

### **After (Composable):**
```python
# Test each graph independently!

def test_kitchen_graph():
    """Test kitchen graph in isolation"""
    kitchen_graph = build_kitchen_graph(llm)
    result = kitchen_graph.invoke({"messages": [...]})
    assert "recipe" in result

def test_chef_graph():
    """Test chef with mocked subgraphs"""
    mock_kitchen = Mock()
    mock_inventory = Mock()
    
    chef_graph = build_chef_graph_with_mocks(
        kitchen=mock_kitchen,
        inventory=mock_inventory
    )
    # Test chef routing logic without running actual tools!
```

---

## 🎯 **FINAL STRUCTURE FOR ROA**

```
roa-agent/
├── agents/
│   ├── factory.py                  # create_react_agent wrappers
│   └── teams/
│       ├── kitchen/
│       │   ├── recipe.py
│       │   ├── team_pm.py
│       │   └── dish_ideation.py
│       ├── inventory/
│       └── sales/
│
├── tools/
│   ├── registry.py                 # ← TOOL_REGISTRY (single source!)
│   ├── recipe_tools.py
│   ├── team_tools.py
│   └── inventory_tools.py
│
├── graphs/                         # ← Composable builders
│   ├── kitchen_graph.py
│   ├── inventory_graph.py
│   ├── sales_graph.py
│   ├── chef_graph.py               # Composes above 3
│   └── root_graph.py               # Composes everything
│
├── state/
│   └── state.py                    # State definition
│
├── utils/
│   ├── node_factory.py             # create_worker_node, etc
│   ├── circuit_breaker.py
│   └── evaluator.py
│
├── config/
│   ├── settings.py
│   └── agents.yaml                 # Agent metadata (optional)
│
├── tests/
│   ├── test_kitchen_graph.py       # ← Test in isolation!
│   ├── test_chef_graph.py
│   └── test_root_graph.py
│
├── agent.py                        # ← Main (now 50 lines!)
├── requirements.txt
└── langgraph.json
```

---

## ✅ **SUMMARY: No Library Needed - Just Patterns**

### **What You Need:**

1. **Tool Registry** → Single source of truth
2. **Factory Functions** → Eliminate duplication
3. **Graph Builders** → Composable modules
4. **Folder Structure** → Separate concerns

### **NOT Libraries:**
- ❌ No special npm/pip package
- ❌ No framework change needed
- ❌ No dependencies to add

### **Just Patterns:**
- ✅ Factory pattern (node wrappers)
- ✅ Registry pattern (tools)
- ✅ Builder pattern (graphs)
- ✅ Composition pattern (subgraphs)

---

## 📊 **BENEFITS FOR ROA:**

| Metric | Before | After |
|--------|--------|-------|
| **Lines in agent.py** | 1285 | ~50 |
| **Node wrappers** | 156 lines | 15 lines |
| **Tool declarations** | 7 places | 1 place |
| **Testability** | Only end-to-end | Each graph isolated |
| **Composability** | None | Full |

---

## 🎯 **RECOMMENDATION:**

**Don't look for a library - apply these 3 patterns:**

1. **Tool Registry** (30 min)
2. **Factory Functions** (1 hour)  
3. **Composable Graphs** (2 hours)

**Total time:** ~3.5 hours  
**Result:** Clean, composable, testable code with LangGraph!

---

**Want me to implement this refactoring for ROA?**
