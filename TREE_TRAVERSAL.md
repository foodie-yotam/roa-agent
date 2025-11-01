# 🌳 Tree Traversal Circuit Breaker

## 🎯 Philosophy

The delegation system is a **tree** that we traverse like Dijkstra or A* search:
- Each **supervisor = decision node**
- Each **worker = branch**
- **Failed worker → backtrack, try alternative branch**
- **All branches failed → escalate to parent**

---

## 🏗️ Tree Structure

```
root (supervisor)
├─ chef_team (supervisor)
│  ├─ kitchen_team (supervisor)
│  │  ├─ recipe (agent)          ← tool fails
│  │  ├─ dish (agent)             ← alternative branch
│  │  └─ team_management (agent)
│  ├─ inventory_team (supervisor)
│  └─ sales_team (supervisor)
├─ visualization (agent)
├─ marketing (agent)
└─ builder_team (supervisor)
```

---

## 🔄 Example: "What kitchens are available?"

### **Scenario: Missing Tool (list_kitchens)**

```
USER: "what kitchens are available?"

─────────────────────────────────────────────
PATH ATTEMPT #1: root → chef_team → recipe
─────────────────────────────────────────────

[root supervisor]
  📍 DELEGATION: root -> chef_team
  Decision: "User asking about kitchens → route to chef_team"

[chef_team supervisor]
  📍 DELEGATION: root -> chef_team -> recipe
  Decision: "Kitchen question → route to recipe agent"

[recipe agent]
  🔧 Calls search_recipes() → NO list_kitchens() tool
  Response: "I cannot list kitchens. I can only search BY kitchen name."
  
[chef_team supervisor]
  ❌ PATH FAILED: root -> chef_team -> recipe
     Reason: Worker reported limitation
     Total failed paths: 1/5
  
  🔄 BACKTRACKING: Supervisor will try alternative route...
  📍 DELEGATION: root -> chef_team -> dish (attempt #2)
  Decision: "Recipe failed, try dish agent (alternative branch)"

[dish agent]
  🔧 Checks available tools
  Response: "I manage dish descriptions, not kitchen listings."
  
[chef_team supervisor]
  ❌ PATH FAILED: root -> chef_team -> dish
     Reason: Worker reported limitation
     Total failed paths: 2/5
  
  ⚠️ LOCAL CIRCUIT BREAKER: 2 attempts at 'root->chef_team'
     Action: ESCALATE UP to parent supervisor

[root supervisor]
  🔄 Chef team exhausted, trying alternative top-level worker
  📍 DELEGATION: root -> visualization
  Decision: "Maybe visualization can help?"

[visualization agent]
  Response: "I create visual displays, I cannot list data sources."
  
[root supervisor]
  ❌ PATH FAILED: root -> visualization
     Total failed paths: 3/5
  
  📍 DELEGATION: root -> builder_team
  Decision: "Last resort - maybe dev tools can help"

[builder_team]
  Response: "I'm for code generation, not data queries."
  
[root supervisor]
  ❌ PATH FAILED: root -> builder_team
     Total failed paths: 4/5
  
  ⚠️ All workers at root level exhausted
  
  🔴 Sends user message:
  "⚠️ I've exhausted all available approaches (4 attempts). 
   I cannot complete this request with current tools. 
   Please try a different request or contact support."
```

---

## ✅ Example: Successful Backtracking

### **Scenario: Database Temporary Failure**

```
USER: "get Arroz Sushi recipe"

─────────────────────────────────────────────
PATH ATTEMPT #1: root → chef_team → recipe
─────────────────────────────────────────────

[recipe agent]
  🔧 Calls search_recipes("Arroz Sushi")
  ❌ Neo4j connection timeout
  
[chef_team supervisor]
  ❌ PATH FAILED: root -> chef_team -> recipe
  🔄 BACKTRACKING...
  
  📍 DELEGATION: root -> chef_team -> recipe (retry #2)
  Decision: "Retry same worker (temporary failure)"

[recipe agent]
  🔧 Calls search_recipes("Arroz Sushi") 
  ✅ Neo4j responds!
  Response: "Found Arroz Sushi recipe with 12 ingredients..."

[chef_team supervisor]
  ✅ PATH SUCCESS: root -> chef_team -> recipe
  Reset counters, task complete!

USER sees: Recipe details ✅
```

---

## 🎯 Circuit Breaker Levels

### **1. Local Level (Per Supervisor)**

```python
MAX_ATTEMPTS_PER_LEVEL = 2
```

**Applies to:** Each individual supervisor's attempts

**Example:**
```
chef_team supervisor:
  Attempt 1: recipe → fails
  Attempt 2: dish → fails
  → LOCAL BREAKER TRIPS → escalate to root
```

**Benefit:** Prevents one supervisor from looping forever

---

### **2. Global Level (Entire Conversation)**

```python
MAX_TOTAL_PATH_FAILURES = 5
```

**Applies to:** All failed paths across the entire tree

**Example:**
```
Failed paths:
1. root -> chef_team -> recipe
2. root -> chef_team -> dish  
3. root -> visualization
4. root -> marketing
5. root -> builder_team

→ GLOBAL BREAKER TRIPS → end conversation
```

**Benefit:** Prevents exploring every possible path if nothing works

---

## 📊 State Tracking

### **delegation_path** (current path)
```python
["root", "chef_team", "recipe"]
```
Shows where we are in the tree

---

### **failed_paths** (tried and failed)
```python
[
  ["root", "chef_team", "recipe"],
  ["root", "chef_team", "dish"],
  ["root", "visualization"]
]
```
Prevents retrying failed paths

---

### **attempts_at_level** (attempts per supervisor)
```python
{
  "root": 1,
  "root->chef_team": 2,  # Hit local limit!
  "root->chef_team->kitchen_team": 0
}
```
Tracks how many times each supervisor tried

---

## 🔍 Decision Logic

```python
def check_circuit_breaker(state, worker_name, supervisor_name):
    # 1. Check global limit
    if len(failed_paths) >= MAX_TOTAL_PATH_FAILURES:
        return "fail"  # Give up entirely
    
    # 2. Check local limit (this supervisor)
    if attempts_at_level[current_level] >= MAX_ATTEMPTS_PER_LEVEL:
        return "escalate_up"  # Parent should try different approach
    
    # 3. Check if path already failed
    if potential_path in failed_paths:
        return "try_alternative"  # Pick different worker
    
    # 4. Safe to try
    return "allow"
```

---

## 🎮 Supervisor Behavior

### **On Worker Failure:**

```python
# Worker says "I cannot do X"
→ record_delegation_failure(state, worker_name, reason)
→ Backtrack: delegation_path.pop()  # Remove failed worker
→ Supervisor runs AGAIN → picks alternative worker
```

### **On Local Breaker Trip:**

```python
# Tried MAX_ATTEMPTS_PER_LEVEL times
→ escalate_up: return FINISH to parent
→ Parent supervisor takes over
```

### **On Global Breaker Trip:**

```python
# Tried MAX_TOTAL_PATH_FAILURES paths
→ Send user: "All approaches exhausted"
→ END conversation
```

---

## 🌟 Key Advantages

### **1. Intelligent Backtracking**
- Failed path → try alternative
- Not stuck with first choice

### **2. Hierarchical Escalation**
- Local supervisor exhausted → parent tries different approach
- Multi-level fallback system

### **3. Exploration Limits**
- Won't try every possible path
- Global limit prevents brute force

### **4. Path Memory**
- Never retry exact same path
- Efficient search

### **5. Graceful Degradation**
- Try reasonable alternatives first
- Clear message when all fail

---

## 🧪 Test Scenarios

### **Test 1: Simple Failure → Alternative**
```bash
chef_team tries: recipe → fails
chef_team tries: dish → succeeds ✅
```

### **Test 2: Local Escalation**
```bash
chef_team tries: recipe → fails
chef_team tries: dish → fails
chef_team → LOCAL BREAKER → escalate to root
root tries: visualization → succeeds ✅
```

### **Test 3: Global Failure**
```bash
Try 5 different paths → all fail
GLOBAL BREAKER → end with message ✅
```

---

## 📝 Configuration

```python
# In agent.py

MAX_ATTEMPTS_PER_LEVEL = 2    # Per supervisor attempts
MAX_TOTAL_PATH_FAILURES = 5   # Global limit

# Adjust based on:
# - Tree depth (deeper tree → higher global limit)
# - Worker count (more workers → more attempts needed)
# - Tolerance for exploration vs. speed
```

---

## 🚀 Future Enhancements

### **1. Cost-Based Search**
```python
# Prioritize cheaper paths first
worker_costs = {"recipe": 1, "visualization": 3}
```

### **2. Heuristic Guidance (A*)**
```python
# Use routing_recommendations as heuristic
heuristic_score = calculate_relevance(worker, user_query)
```

### **3. Path Caching**
```python
# Remember successful paths for similar queries
if similar_query_exists:
    try_cached_path_first()
```

### **4. Dynamic Limits**
```python
# Adjust limits based on query complexity
if simple_query:
    MAX_ATTEMPTS = 2
else:
    MAX_ATTEMPTS = 4
```

---

## ✅ Summary

**OLD (Rigid):**
```
Worker fails 2x → STOP EVERYTHING
```

**NEW (Smart):**
```
Worker fails → try alternative worker
Supervisor exhausted → escalate to parent
All paths fail → stop gracefully
```

**Result:** Flexible, intelligent, explores alternatives, prevents infinite loops! 🎉

---

**Implementation Date:** 2025-10-31  
**Commit:** (pending)  
**Branch:** `dev`  
**Architecture:** Tree traversal with backtracking (Dijkstra/A*-style)
