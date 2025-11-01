# 🔍 Tool Visibility - Informed Supervisors

## 🎯 Philosophy

**Supervisors are INFORMED MANAGERS, not blind explorers.**

With complete tool visibility, supervisors:
- ✅ See ALL subordinate tools upfront (name, args, description, examples)
- ✅ Match user request to available tools BEFORE delegating
- ✅ Route correctly on FIRST attempt (no trial-and-error)
- ✅ Respond FINISH immediately if no tool exists (don't waste attempts)

---

## 📋 Tool Table Format

Supervisors receive a comprehensive tool table in their system prompt:

```
====================================================================================================
AVAILABLE TOOLS (by Worker):
====================================================================================================

📦 RECIPE:
----------------------------------------------------------------------------------------------------
  🔧 search_recipes
     Description: Search for recipes in the database
     Args: ['kitchen_name', 'recipe_name']
     
  🔧 get_recipe_details
     Description: Get detailed recipe information including ingredients
     Args: ['recipe_name', 'kitchen_name']
     

📦 TEAM_PM:
----------------------------------------------------------------------------------------------------
  🔧 get_team_members
     Description: Get list of team members
     Args: []
     
  🔧 assign_task
     Description: Assign a task to a team member
     Args: ['task', 'assignee']
     

📦 DISH_IDEATION:
----------------------------------------------------------------------------------------------------
  🔧 suggest_dishes
     Description: Suggest new dish ideas based on current ingredients
     Args: ['ingredients']
     

====================================================================================================
```

---

## 🏗️ Hierarchical Tool Visibility

### **Leaf Supervisors** (see direct workers)

**kitchen_supervisor** sees:
```python
{
    "recipe": [search_recipes, get_recipe_details],
    "team_pm": [get_team_members, assign_task],
    "dish_ideation": [suggest_dishes]
}
```

**inventory_supervisor** sees:
```python
{
    "stock": [check_stock],
    "suppliers": [list_suppliers],
    "analysis": [forecast_demand]
}
```

---

### **Meta Supervisors** (see all subteam tools)

**chef_supervisor** sees:
```python
{
    "kitchen_team": [
        search_recipes, get_recipe_details,  # from recipe
        get_team_members, assign_task,        # from team_pm
        suggest_dishes                        # from dish_ideation
    ],
    "inventory_team": [
        check_stock,                          # from stock
        list_suppliers,                       # from suppliers
        forecast_demand                       # from analysis
    ],
    "sales_team": [
        calculate_cost                        # from profit
    ]
}
```

---

### **Root Supervisor** (sees entire system)

**root_supervisor** sees:
```python
{
    "visualization": [
        display_recipes,
        display_multiplication,
        display_prediction_graph,
        display_inventory_alert,
        display_team_assignment
    ],
    "marketing": [
        create_marketing_content
    ],
    "builder_team": [
        generate_tool_code
    ],
    "chef_team": [
        # ALL chef tools from kitchen, inventory, sales
        search_recipes, get_recipe_details,
        get_team_members, assign_task, suggest_dishes,
        check_stock, list_suppliers, forecast_demand,
        calculate_cost
    ]
}
```

---

## 💡 Example: Intelligent Routing with Tool Visibility

### **Scenario 1: User asks "get Arroz Sushi recipe"**

**Root supervisor thinks:**
```
User wants: recipe details
Available tools:
  ✅ chef_team has: search_recipes, get_recipe_details
  ❌ visualization has: display tools (not data retrieval)
  ❌ marketing has: content generation (not data)
  
Decision: Route to chef_team (has needed tools) ✅
```

**Chef supervisor thinks:**
```
User wants: recipe details
Available tools:
  ✅ kitchen_team has: search_recipes, get_recipe_details
  ❌ inventory_team has: stock tools
  ❌ sales_team has: cost tools
  
Decision: Route to kitchen_team ✅
```

**Kitchen supervisor thinks:**
```
User wants: recipe details
Available tools:
  ✅ recipe has: search_recipes, get_recipe_details
  ❌ team_pm has: team management
  ❌ dish_ideation has: suggestions
  
Decision: Route to recipe worker ✅
```

**Result: Perfect routing on first attempt!** ✅

---

### **Scenario 2: User asks "what kitchens are available?"**

**Root supervisor thinks:**
```
User wants: list of kitchens
Available tools:
  chef_team tools:
    - search_recipes (requires kitchen_name) ❌
    - get_recipe_details (requires recipe_name) ❌
    - check_stock (checks inventory, not kitchens) ❌
    
  ❌ NO tool exists to list kitchens
  
Decision: Respond FINISH immediately with:
  "I don't have a tool to list available kitchens. 
   I can search recipes IF you provide a kitchen name."
```

**Result: Immediate clear answer (no wasted routing attempts)** ✅

---

## 🎯 Circuit Breaker with Tool Visibility

With full visibility, circuit breaker is a **SAFETY NET**, not an exploration strategy:

```python
MAX_SAME_WORKER_ATTEMPTS = 2  # Don't retry failed worker
MAX_TOTAL_ATTEMPTS = 3         # Should route correctly first try
```

**Expected behavior:**
- ✅ **Attempt 1:** Route to correct worker (supervisor knows tools)
- ✅ **Success:** Worker completes task
- ❌ **Failure only if:** Bug, temporary error, or missing tool

**Circuit breaker triggers ONLY when:**
1. Supervisor routes to wrong worker (routing bug)
2. Worker fails and supervisor retries (temporary error)
3. 3 total attempts exhausted (something is wrong)

With tool visibility, **supervisor should route correctly on attempt 1** in 99% of cases.

---

## 🔧 Implementation

### **1. Tools have example I/O:**

```python
@tool
def search_recipes(kitchen_name: Optional[str] = None, recipe_name: Optional[str] = None) -> str:
    """Search for recipes in the database
    
    Example Input: kitchen_name="Yotam Kitchen"
    Example Output: "Found 12 recipes: [{'kitchen': 'Yotam Kitchen', 'recipe': 'Arroz Sushi'}, ...]"
    
    Example Input: recipe_name="Arroz Sushi"
    Example Output: "Found 1 recipes: [{'kitchen': 'Yotam Kitchen', 'recipe': 'Arroz Sushi'}]"
    """
```

---

### **2. Supervisors receive worker_tools dict:**

```python
kitchen_supervisor = make_supervisor_node(
    llm, 
    ["recipe", "team_pm", "dish_ideation"], 
    worker_tools={
        "recipe": [search_recipes, get_recipe_details],
        "team_pm": [get_team_members, assign_task],
        "dish_ideation": [suggest_dishes]
    }
)
```

---

### **3. Tool table built automatically:**

```python
def build_tool_table(worker_tools: dict) -> str:
    """Build comprehensive tool visibility table"""
    table = "\nAVAILABLE TOOLS (by Worker):\n"
    
    for worker_name, tools in worker_tools.items():
        table += f"📦 {worker_name.upper()}:\n"
        
        for tool in tools:
            table += f"  🔧 {tool.name}\n"
            table += f"     Description: {tool.description}\n"
            table += f"     Args: {list(tool.args_schema.__fields__.keys())}\n"
    
    return table
```

---

### **4. System prompt includes tool table:**

```python
system_prompt = f"""
⚠️ CRITICAL - TOOL VISIBILITY:
You have COMPLETE VISIBILITY of all tools available to your workers (see table below).
Use this to make INFORMED routing decisions UPFRONT.

With tool visibility, you should:
1. Match user request to available tools
2. Route to worker who HAS the needed tool
3. If NO worker has needed tool → respond FINISH immediately
4. Don't blindly explore - you know what each worker can do!

Your available workers: {members}
{tool_table}
"""
```

---

## 📊 Benefits

### **1. Smart Routing**
- ✅ Correct worker on first attempt
- ✅ No trial-and-error exploration
- ✅ Reduced LLM calls

### **2. Clear Limitations**
- ✅ Supervisor knows when NO tool exists
- ✅ Immediate user feedback
- ✅ No wasted routing attempts

### **3. Debugging**
- ✅ Tool table logged in traces
- ✅ See exactly what supervisor knows
- ✅ Easy to spot missing tools

### **4. Maintenance**
- ✅ Add new tool → automatically visible
- ✅ Tool description in one place
- ✅ Examples help LLM understand behavior

---

## 🚀 Future Enhancements

### **1. Tool Cost Metadata**
```python
@tool
def search_recipes(...) -> str:
    """...
    
    Cost: Low (database query)
    Latency: ~200ms
    """
```

### **2. Tool Success Rate**
```python
# Track which tools work reliably
tool_stats = {
    "search_recipes": {"success_rate": 0.95, "avg_latency": 0.2},
    "forecast_demand": {"success_rate": 0.85, "avg_latency": 1.5}
}
```

### **3. Dynamic Tool Discovery**
```python
# Tools register themselves
tool_registry.register(search_recipes, category="recipe", priority=1)
```

---

## ✅ Summary

**OLD (Blind Exploration):**
```
Supervisor tries: worker1 → fails
Supervisor tries: worker2 → fails
Supervisor tries: worker3 → succeeds
```

**NEW (Informed Decision):**
```
Supervisor sees:
  - worker1 has tool_A, tool_B
  - worker2 has tool_C
  - worker3 has tool_D, tool_E
  
User needs: tool_D
Supervisor routes: worker3 (has tool_D) ✅
```

**Result: Intelligent managers making informed decisions! 🎯**

---

**Implementation Date:** 2025-11-01  
**Commit:** `80385ad`, `bb4e8ad`  
**Branch:** `dev`  
**Status:** ✅ Full tool visibility implemented across all supervisors
