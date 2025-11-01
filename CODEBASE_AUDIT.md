# 🔍 Codebase Audit - Complexity & Duplication Report

**Date:** 2025-11-02  
**File:** `agent.py` (1285 lines)  
**Status:** ⚠️ Growing spaghetti - needs refactoring

---

## 🚨 **ISSUES FOUND**

### **1. MASSIVE CODE DUPLICATION** 🔴

**Problem:** 13 nearly-identical node wrapper functions

**Current Pattern (repeated 13x):**
```python
def recipe_node(state: State) -> Command[Literal["supervisor"]]:
    result = recipe_agent.invoke(state)
    return Command(
        update={"messages": [HumanMessage(content=result["messages"][-1].content, name="recipe")]},
        goto="supervisor"
    )

def team_pm_node(state: State) -> Command[Literal["supervisor"]]:
    result = team_pm_agent.invoke(state)
    return Command(
        update={"messages": [HumanMessage(content=result["messages"][-1].content, name="team_pm")]},
        goto="supervisor"
    )

# ... 11 MORE identical patterns!
```

**Lines wasted:** ~156 lines (13 functions × 12 lines each)

**Solution:** Factory function
```python
def create_worker_node(agent_name, agent):
    """Factory: Creates node wrapper for any agent"""
    def node(state: State) -> Command[Literal["supervisor"]]:
        result = agent.invoke(state)
        return Command(
            update={"messages": [HumanMessage(
                content=result["messages"][-1].content,
                name=agent_name
            )]},
            goto="supervisor"
        )
    return node

# Usage (1 line per agent instead of 12):
recipe_node = create_worker_node("recipe", recipe_agent)
team_pm_node = create_worker_node("team_pm", team_pm_agent)
```

**Impact:** 156 lines → 15 lines (90% reduction!)

---

### **2. FRAGILE TOOL REGISTRATION** 🔴

**Problem:** Tools manually listed in 7 different places

**Example:**
```python
# Place 1: Creating agent
recipe_agent = create_react_agent(llm, [search_recipes, get_recipe_details], ...)

# Place 2: Passing to supervisor
kitchen_supervisor = make_supervisor_node(..., worker_tools={
    "recipe": [search_recipes, get_recipe_details],  # ← Duplicated!
    ...
})
```

**Risk:** Add a tool to agent, forget to add to supervisor → broken visibility

**Solution:** Single source of truth
```python
TOOL_REGISTRY = {
    "recipe": [search_recipes, get_recipe_details],
    "team_pm": [get_team_members, assign_task],
    "dish_ideation": [suggest_dishes],
    # ... etc
}

# Usage
recipe_agent = create_react_agent(llm, TOOL_REGISTRY["recipe"], ...)
kitchen_supervisor = make_supervisor_node(llm, [...], worker_tools=TOOL_REGISTRY)
```

---

### **3. REDUNDANT CIRCUIT BREAKER TRACKING** 🟡

**Problem:** We track delegation BOTH in circuit breaker AND in state

**Duplicated:**
```python
# In State
delegation_path: list
delegation_depth: int
attempts_at_level: dict

# In circuit breaker functions
record_delegation_attempt()  # Updates delegation_path
check_circuit_breaker()      # Checks delegation_depth
```

**Question:** Do we need BOTH?

**Recommendation:** YES - but simplify
- State tracks the PATH (for observability)
- Circuit breaker just CHECKS limits (business logic)

**Current:** Fine, but could be cleaner

---

### **4. SWARM-AS-CODE NOT ACTUALLY USED** 🔴

**Created but not integrated:**
```
swarm_config/
├── swarm.yaml           ✅ Created
├── agents/*.yaml        ✅ Created
└── prompts/*.md         ✅ Created

swarm_loader.py          ✅ Created

agent.py                 ❌ Still hard-coded! Not using swarm_loader!
```

**Problem:** We built Swarm-as-Code but `agent.py` still hard-codes everything!

**Impact:** 
- Can't actually edit YAML to change agents
- CEO can't iterate independently
- All that Swarm-as-Code work is unused decoration

**Fix:** Replace `agent.py` with:
```python
from swarm_loader import load_swarm
agent = load_swarm("swarm_config/swarm.yaml")
```

---

### **5. OVERCOMPLICATED STATE** 🟡

**Current State has 8 fields:**
```python
class State(MessagesState):
    next: str
    routing_recommendations: str
    delegation_path: list
    failed_paths: list
    attempts_at_level: dict
    delegation_depth: int
    max_delegation_depth: int
```

**Question:** Do we need all of these?

**Analysis:**
- `messages` ✅ Required (LangGraph)
- `next` ✅ Required (routing)
- `routing_recommendations` ⚠️ Only used by conversational agent
- `delegation_path` ✅ Needed for observability
- `failed_paths` ⚠️ Never actually used?
- `attempts_at_level` ✅ Circuit breaker needs
- `delegation_depth` ✅ Circuit breaker needs
- `max_delegation_depth` ⚠️ Could be constant

**Recommendation:** Remove `failed_paths` if not used, make `max_delegation_depth` a constant

---

### **6. EVALUATOR NOT INTEGRATED** 🟡

**Created:** `evaluate_worker_output()` function  
**Used:** Nowhere in the code!

**Impact:** We have quality validation but it's not hooked up

**Where to add:**
```python
def supervisor_node(state: State):
    # ... route to worker ...
    
    # After worker responds:
    worker_output = state["messages"][-1].content
    evaluation = evaluate_worker_output(task, worker_output, llm)
    
    if not evaluation["is_sufficient"]:
        # Retry with critique
        return route_with_feedback(evaluation["critique"])
```

**Status:** Built but not used = dead code

---

## 📊 **CODE METRICS**

| Metric | Current | Could Be | Savings |
|--------|---------|----------|---------|
| **Total Lines** | 1285 | ~800 | 37% |
| **Node Functions** | 13 × 12 lines | 13 × 1 line | 90% |
| **Tool Declarations** | 7 places | 1 place | 85% |
| **Hard-coded agents** | 100% | 0% (YAML) | 100% |

---

## 🎯 **RECOMMENDED FRAMEWORKS** (Research Results)

### **Current: LangGraph (DIY)**
**Pros:** ✅ Most flexible, full control  
**Cons:** ❌ Too much boilerplate, manual work

### **Option 1: Keep LangGraph but Simplify**
**Recommendation:** ✅ Best choice - you're already invested

**Changes needed:**
1. Use factory functions (eliminate duplication)
2. Actually use swarm_loader.py
3. Tool registry (single source of truth)
4. Remove dead code (evaluator, failed_paths)

**Result:** Same architecture, 40% less code

---

### **Option 2: Switch to CrewAI** 
**Pros:**
- Role-based agents (built-in)
- YAML configuration (native)
- Less boilerplate

**Cons:**
- Different architecture (sequential, not hierarchical)
- Migration cost high
- Less control than LangGraph

**Recommendation:** ❌ Not worth switching

---

### **Option 3: Microsoft Agent Framework** (NEW - Oct 2024)
**Features:**
- YAML/JSON declarative config (native!)
- Enterprise-grade
- Integrates with Azure

**Pros:**
- Purpose-built for what you want
- Official Microsoft backing

**Cons:**
- Very new (just released)
- Tied to Azure ecosystem?
- Limited community

**Recommendation:** ⏳ Watch this space, not ready yet

---

## ✅ **ACTION PLAN**

### **Phase 1: Remove Duplication (2 hours)**
```python
# 1. Factory for worker nodes
def create_worker_node(name, agent):
    # ...

# 2. Tool registry
TOOLS = {
    "recipe": [search_recipes, get_recipe_details],
    # ...
}

# 3. Use factory
nodes = {
    name: create_worker_node(name, agent)
    for name, agent in agents.items()
}
```

**Impact:** 156 lines → 15 lines

---

### **Phase 2: Actually Use Swarm-as-Code (3 hours)**
```python
# OLD agent.py (1285 lines):
# ... hard-coded everything ...

# NEW agent.py (50 lines):
from swarm_loader import load_swarm

# Load from config
swarm = load_swarm("swarm_config/swarm.yaml")

# Done!
```

**Impact:** 1285 lines → 50 lines + YAML files

---

### **Phase 3: Clean Dead Code (30 min)**
- Remove `failed_paths` from State (not used)
- Remove or integrate `evaluate_worker_output()` 
- Make `max_delegation_depth` a constant

**Impact:** Cleaner, less confusing

---

### **Phase 4: Tool Registry (1 hour)**
```python
# Single source of truth
TOOL_REGISTRY = {
    "recipe": [search_recipes, get_recipe_details],
    # ...
}

# Everything pulls from here
agent = create_react_agent(llm, TOOL_REGISTRY[name], ...)
supervisor = make_supervisor_node(llm, [...], worker_tools=TOOL_REGISTRY)
```

**Impact:** No more forgetting to update both places

---

## 🎯 **VERDICT**

### **Current State:**
- ⚠️ **Growing spaghetti** - lots of duplication
- ⚠️ **Swarm-as-Code unused** - built but not integrated
- ⚠️ **Dead code** - evaluator exists but not hooked up
- ⚠️ **Fragile** - tools declared in 7 places

### **Recommendation:**
**STICK WITH LANGGRAPH** but apply these fixes:

1. **Factory functions** (eliminate 90% duplication)
2. **Actually use swarm_loader** (make YAML work)
3. **Tool registry** (single source of truth)
4. **Remove dead code** (failed_paths, unused evaluator)

**Result:**
- Same architecture
- Same capabilities
- 40% less code
- Way more maintainable
- YAML actually works!

---

## 🚀 **FRAMEWORK VERDICT** (from research)

**Best frameworks in 2024:**

1. **LangGraph** ← YOU (best for complex hierarchies)
   - Most flexible
   - Production-ready
   - Backed by LangChain

2. **CrewAI** (best for role-based teams)
   - Easier to start
   - Less flexible
   - Good for simpler cases

3. **AutoGen** (best for conversations)
   - Free-flowing dialogue
   - Less structured
   - Research-focused

4. **OpenAI Swarm** (experimental)
   - Lightweight
   - Not production-ready
   - Educational

**Recommendation for ROA:** **Stick with LangGraph**, just clean it up!

---

## 📝 **Summary**

**Don't switch frameworks - fix the code!**

**Problems:**
1. 156 lines of duplicated node wrappers
2. Tools declared in 7 different places
3. Swarm-as-Code built but not used
4. Dead code (evaluator, failed_paths)

**Solutions:**
1. Factory functions → 90% less duplication
2. Tool registry → single source of truth
3. Use swarm_loader → YAML actually works
4. Remove dead code → clearer intent

**Time:** ~6 hours total  
**Impact:** 40% less code, 100% more maintainable

**Want me to implement these fixes?**
