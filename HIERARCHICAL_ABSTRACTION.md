# 🏢 Hierarchical Information Abstraction

## 🎯 Philosophy

**The further a manager is from workers, the less detail they need.**

Like real organizations:
- ✅ **Direct supervisor** knows every tool their reports have
- ⚠️ **Middle manager** knows team capabilities (abstract)
- 📊 **Executive** knows department purpose (very abstract)

**Why?**
- Reduces context flooding
- Enables scalability (add 100 tools, CEO still has same context)
- Mirrors human organizational hierarchies
- Forces proper delegation

---

## 📊 Current ROA Hierarchy

```
root (CEO level)
├─ visualization (direct report) → DETAILED: sees all 5 viz tools
├─ marketing (direct report) → DETAILED: sees create_marketing_content
├─ builder_team (direct report) → DETAILED: sees generate_tool_code
└─ chef_team (meta-team) → ABSTRACT: "Handles kitchen operations..."
   ├─ kitchen_team (team supervisor) → ABSTRACT at chef level
   │  ├─ recipe (worker) → DETAILED at kitchen level
   │  ├─ team_pm (worker) → DETAILED at kitchen level
   │  └─ dish_ideation (worker) → DETAILED at kitchen level
   ├─ inventory_team (team supervisor) → ABSTRACT at chef level
   └─ sales_team (team supervisor) → ABSTRACT at chef level
```

---

## 🔍 Information Visibility by Layer

### **Layer 0: Root Supervisor** (3 layers from tools)

**Sees:**
```yaml
visualization:
  - display_recipes       # DETAILED (direct report)
  - display_multiplication
  - display_prediction_graph
  - display_inventory_alert
  - display_team_assignment

marketing:
  - create_marketing_content  # DETAILED (direct report)

builder_team:
  - generate_tool_code         # DETAILED (direct report)

chef_team:
  description: "Handles ALL kitchen operations: recipes, inventory, team management, cost analysis, and sales planning."  # ABSTRACT (meta-team)
```

**Root doesn't need to know:**
- ❌ That kitchen_team has `search_recipes` with args `(kitchen_name, recipe_name)`
- ❌ That recipe agent uses Neo4j queries
- ❌ Individual tool signatures

**Root only needs to know:**
- ✅ chef_team handles "kitchen operations"
- ✅ Delegate recipe requests to chef_team

---

### **Layer 1: Chef Supervisor** (2 layers from tools)

**Sees:**
```yaml
kitchen_team:
  description: "Manages recipes, team assignments, and dish planning. Handles: searching recipes, getting recipe details, managing team members, and suggesting new dishes."

inventory_team:
  description: "Tracks inventory and supplier relationships. Handles: checking stock levels, listing suppliers, and forecasting demand."

sales_team:
  description: "Analyzes costs and profitability. Handles: calculating recipe costs and profit margins."
```

**Chef doesn't need to know:**
- ❌ Exact tool names (`search_recipes` vs `find_recipes`)
- ❌ Tool arguments (`kitchen_name: Optional[str]`)
- ❌ Implementation details (Neo4j queries, rapidfuzz)

**Chef only needs to know:**
- ✅ kitchen_team can search/retrieve recipes
- ✅ inventory_team can check stock
- ✅ sales_team can calculate costs

---

### **Layer 2: Kitchen Supervisor** (1 layer from tools)

**Sees:**
```yaml
recipe:
  tools:
    - search_recipes:
        description: "Search for recipes with optional fuzzy matching support"
        args: [kitchen_name, recipe_name]
    - get_recipe_details:
        description: "Get recipe details with optional fuzzy matching fallback"
        args: [recipe_name, kitchen_name]

team_pm:
  tools:
    - get_team_members:
        args: [kitchen_name]
    - assign_task:
        args: [member, task]

dish_ideation:
  tools:
    - suggest_dishes:
        args: [ingredients]
```

**Kitchen DOES need to know:**
- ✅ Exact tool names
- ✅ Tool arguments
- ✅ What each tool does
- ✅ When to call which tool

**Why?** Kitchen supervisor is DIRECTLY managing these workers.

---

## 📈 Benefits

### **1. Context Efficiency**

**Before (no abstraction):**
```
Root system prompt: 15,000 tokens
- All 50 tools listed with full details
- Every argument documented
- Every example shown
```

**After (with abstraction):**
```
Root system prompt: 3,000 tokens
- 3 detailed tool lists (direct reports)
- 1 abstract description (chef_team)
- 80% token reduction!
```

---

### **2. Scalability**

**Scenario: Add 20 new recipe tools**

**Before:**
- Root supervisor context grows by 5,000 tokens ❌
- Every manager sees all new tools ❌
- System-wide context inflation ❌

**After:**
- Root supervisor: No change (still sees "kitchen operations") ✅
- Chef supervisor: Update abstract description slightly ✅
- Kitchen supervisor: Sees all 20 tools (needs to route correctly) ✅

---

### **3. Proper Delegation**

**Without abstraction:**
```
User: "What recipes do we have?"

Root: *sees search_recipes tool*
      *might try to route directly to recipe agent*
      ❌ Bypasses intermediate supervisors!
```

**With abstraction:**
```
User: "What recipes do we have?"

Root: *sees "chef_team handles kitchen operations"*
      ✅ Routes to chef_team

Chef: *sees "kitchen_team manages recipes"*
      ✅ Routes to kitchen_team

Kitchen: *sees search_recipes tool*
          ✅ Routes to recipe agent
```

**Result:** Proper hierarchical delegation! No shortcutting.

---

## 🛠️ Implementation

### **build_tool_table() Function**

```python
def build_tool_table(worker_tools: dict, detail_level: str = "full") -> str:
    """
    Args:
        worker_tools: {
            "worker_name": [list of tools],      # Detailed
            "team_name": "description string"    # Abstract
        }
    """
    for worker_name, worker_info in worker_tools.items():
        if isinstance(worker_info, str):
            # Abstract - just show description
            print(f"{worker_name}: {worker_info}")
        elif isinstance(worker_info, list):
            # Detailed - show all tools
            for tool in worker_info:
                print(f"  - {tool.name}: {tool.description}")
```

---

### **Supervisor Configuration**

```python
# Direct reports → DETAILED
kitchen_supervisor = make_supervisor_node(
    llm, 
    ["recipe", "team_pm", "dish_ideation"], 
    worker_tools={
        "recipe": [search_recipes, get_recipe_details],  # Full detail
        "team_pm": [get_team_members, assign_task],
        "dish_ideation": [suggest_dishes]
    }
)

# Meta-team → ABSTRACT
chef_supervisor = make_supervisor_node(
    llm,
    ["kitchen_team", "inventory_team", "sales_team"],
    worker_tools={
        "kitchen_team": "Manages recipes and team assignments",  # Abstract
        "inventory_team": "Tracks stock and suppliers",
        "sales_team": "Analyzes costs and profitability"
    }
)
```

---

## 📋 Abstraction Rules

### **When to show DETAILED (tool list):**
- ✅ Direct reports (1 layer away)
- ✅ Simple worker agents (not teams)
- ✅ Need to choose specific tool to call

### **When to show ABSTRACT (description):**
- ✅ Teams/meta-teams (2+ layers away)
- ✅ Supervisor needs to delegate, not execute
- ✅ Tool details would flood context

---

## 🎯 Example: "Get Arroz Sushi Recipe"

### **Root Supervisor Sees:**
```
chef_team: "Handles ALL kitchen operations: recipes, inventory, team management..."
```

**Decision:** User wants recipe → route to chef_team ✅

---

### **Chef Supervisor Sees:**
```
kitchen_team: "Manages recipes, team assignments, and dish planning. Handles: searching recipes, getting recipe details..."
```

**Decision:** User wants recipe → route to kitchen_team ✅

---

### **Kitchen Supervisor Sees:**
```
recipe:
  - search_recipes(kitchen_name?, recipe_name?)
  - get_recipe_details(recipe_name, kitchen_name?)
    
team_pm:
  - get_team_members(kitchen_name)
  - assign_task(member, task)
```

**Decision:** User wants recipe details → route to recipe agent → call get_recipe_details("Arroz Sushi") ✅

---

## ✅ Summary

| Level | Distance | Visibility | Example |
|-------|----------|------------|---------|
| **Root** | 3 layers | Very Abstract | "chef_team handles kitchen ops" |
| **Chef** | 2 layers | Abstract | "kitchen_team manages recipes" |
| **Kitchen** | 1 layer | Detailed | "search_recipes(kitchen_name, recipe_name)" |
| **Worker** | 0 layers | Full Implementation | Neo4j queries, fuzzy matching, etc. |

**Result:** Clean delegation hierarchy with context efficiency! 🎉

---

**Implementation Date:** 2025-11-01  
**Commit:** (pending)  
**Branch:** `dev`  
**Principle:** Information hiding scales agent swarms
