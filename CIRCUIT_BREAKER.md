# ⚡ Circuit Breaker System - 2-Failed-Delegation Limit

## 🎯 Purpose

**Prevent infinite loops** by limiting failed delegations to any worker (subagent or tool) to a maximum of **2 attempts** per conversation.

---

## 🔴 The Problem

**Before Circuit Breaker:**
```
User: "what kitchens are available?"
  ↓
supervisor → routes to chef_team
  ↓
chef_team → "I cannot list kitchens"
  ↓
supervisor → routes to chef_team (AGAIN!)
  ↓
chef_team → "I cannot list kitchens" (AGAIN!)
  ↓
... loops 14 times ...
```

**Cost:** 14x LLM calls, wasted compute, poor UX

---

## ✅ The Solution

**With Circuit Breaker:**
```
User: "what kitchens are available?"
  ↓
supervisor → routes to chef_team
  ↓
chef_team → "I cannot list kitchens"
  ↓
[FAILURE #1 RECORDED]
  ↓
supervisor → routes to chef_team (retry)
  ↓
chef_team → "I cannot list kitchens"
  ↓
[FAILURE #2 RECORDED]
  ↓
🔴 CIRCUIT BREAKER TRIPS
  ↓
User sees: "⚠️ Safety limit reached: chef_team has failed 2+ times. 
            I cannot complete this request with current tools. 
            Please try a different approach or contact support."
  ↓
END (no more attempts)
```

**Benefit:** Stops after 2 failures, saves compute, clear user feedback

---

## 🏗️ Architecture

### **State Tracking**

```python
class State(MessagesState):
    delegation_failures: dict  # {"worker_name": failure_count}
```

**Example:**
```python
{
    "delegation_failures": {
        "chef_team": 2,      # Failed 2 times - circuit breaker will trip
        "visualization": 1,  # Failed once - can retry
        "marketing": 0       # No failures
    }
}
```

---

### **Core Functions**

#### **1. `record_delegation_failure(state, worker_name, reason)`**

Records when a worker fails.

**Triggers:**
- Worker reports limitation: "cannot", "unable to", "don't have"
- Tool call fails
- Worker returns without completing task

**Example:**
```python
update_data = record_delegation_failure(
    state, 
    "chef_team", 
    "Worker reported: I do not have ability to list kitchens"
)
# Returns: {"delegation_failures": {"chef_team": 1}}
```

---

#### **2. `check_circuit_breaker(state, worker_name)`**

Checks if worker can be delegated to.

**Returns:**
```python
(can_delegate: bool, reason: str)
```

**Example:**
```python
can_delegate, reason = check_circuit_breaker(state, "chef_team")

if not can_delegate:
    # reason = "CIRCUIT BREAKER: chef_team has failed 2 times (limit: 2)"
    # Stop delegation, inform user
```

---

### **Supervisor Integration**

Every supervisor now:

1. **Detects failures** from worker responses
2. **Records failures** in state
3. **Checks circuit breaker** before delegating
4. **Trips breaker** if limit exceeded

**Code Flow:**
```python
def supervisor_node(state: State):
    # 1. Check if last worker reported error
    if worker_reported_limitation(last_message):
        update = record_delegation_failure(state, worker_name, reason)
        return Command(goto=END, update=update)
    
    # 2. Decide routing
    goto = llm_routing_decision()
    
    # 3. Check circuit breaker BEFORE delegating
    can_delegate, reason = check_circuit_breaker(state, goto)
    if not can_delegate:
        return send_circuit_breaker_message()
    
    # 4. Safe to delegate
    return Command(goto=goto)
```

---

## 📊 Configuration

### **Adjustable Limit**

```python
MAX_DELEGATION_FAILURES = 2  # Top of agent.py
```

**Change to 3 for more retries:**
```python
MAX_DELEGATION_FAILURES = 3
```

**Change to 1 for stricter policy:**
```python
MAX_DELEGATION_FAILURES = 1
```

---

## 🎯 What Counts as a "Failure"

### ✅ **Counted as Failure:**

1. **Worker Limitations**
   - "I cannot do X"
   - "I don't have the ability to Y"
   - "Unable to complete Z"

2. **Tool Failures**
   - Tool raises exception
   - Tool returns error message
   - Tool times out

3. **Incomplete Results**
   - Worker returns but task not completed
   - Worker loops back to supervisor

### ❌ **NOT Counted as Failure:**

1. **Successful completions**
   - Worker completes task successfully
   - Returns valid data

2. **Partial success**
   - Worker completes part of task
   - No error indicators in response

3. **Delegation to different worker**
   - Each worker has independent counter
   - `chef_team` failing doesn't affect `visualization` counter

---

## 🔍 Debugging

### **View Failure Counts**

Check state in LangSmith traces:
```python
state["delegation_failures"]
# Output: {"chef_team": 2, "visualization": 1}
```

### **Console Logging**

Circuit breaker logs to console:
```
⚠️  DELEGATION FAILURE: chef_team failed (attempt #1, limit: 2)
   Reason: Worker reported limitation: I do not have ability to list kitchens

⚠️  DELEGATION FAILURE: chef_team failed (attempt #2, limit: 2)
   Reason: Worker reported limitation: I do not have ability to list kitchens

🔴 CIRCUIT BREAKER: chef_team has failed 2 times (limit: 2). Stopping delegation.
```

---

## 📋 Example Scenarios

### **Scenario 1: Missing Tool (Our Bug)**

```
User: "what kitchens are available?"

Attempt 1:
  supervisor → chef_team
  chef_team → "I cannot list kitchens" ❌
  [FAILURE #1 recorded]

Attempt 2:
  supervisor → chef_team (retry)
  chef_team → "I cannot list kitchens" ❌
  [FAILURE #2 recorded]

🔴 Circuit Breaker Trips:
  User sees: "Safety limit reached. Try different approach."
```

---

### **Scenario 2: Database Connection Issues**

```
User: "get Arroz Sushi recipe"

Attempt 1:
  supervisor → chef_team → recipe agent
  recipe agent calls search_recipes()
  Neo4j connection timeout ❌
  [FAILURE #1 recorded for recipe agent]

Attempt 2:
  supervisor → chef_team → recipe agent
  recipe agent calls search_recipes()
  Neo4j connection timeout ❌
  [FAILURE #2 recorded for recipe agent]

🔴 Circuit Breaker Trips:
  User sees: "Safety limit reached. Database may be down."
```

---

### **Scenario 3: Successful Retry**

```
User: "create visualization"

Attempt 1:
  supervisor → visualization
  visualization → temporary error ❌
  [FAILURE #1 recorded]

Attempt 2:
  supervisor → visualization (retry)
  visualization → SUCCESS ✅
  [Failure counter stays at 1, no trip]

✅ User sees successful visualization
```

---

## ⚙️ System-Wide Enforcement

### **All Supervisors Include Policy:**

```python
system_prompt = f"""
⚠️ CIRCUIT BREAKER POLICY (SYSTEM-WIDE):
- Maximum of {MAX_DELEGATION_FAILURES} failed delegations per worker
- Applies to ALL delegations: subagents AND tool calls
- After {MAX_DELEGATION_FAILURES} failures, circuit breaker trips
- Failure = error/limitation OR tool fails OR task incomplete

TERMINATE when circuit breaker trips.
"""
```

---

## 🎓 Benefits

1. **Prevents Infinite Loops**
   - Hard limit on retry attempts
   - System cannot get stuck

2. **Saves Resources**
   - Stops wasting LLM calls
   - Prevents runaway costs

3. **Better UX**
   - Clear error messages
   - User knows system stopped trying

4. **Easier Debugging**
   - Failure counts logged
   - Clear circuit breaker messages

5. **Configurable**
   - Adjust limit based on needs
   - Per-worker tracking

---

## 🚀 Future Enhancements

### **Potential Improvements:**

1. **Per-Tool Limits**
   ```python
   tool_failures: {"search_recipes": 2, "get_recipe_details": 1}
   ```

2. **Exponential Backoff**
   ```python
   delay = 2^attempt_number  # Wait longer between retries
   ```

3. **Circuit Breaker Reset**
   ```python
   if time_since_last_failure > 60:  # Reset after 60 seconds
       reset_failure_counter()
   ```

4. **Alternative Routing**
   ```python
   if chef_team_fails:
       try_alternative_approach()  # Route to different worker
   ```

---

## ✅ Testing

### **Test Circuit Breaker:**

```bash
# In scripts/
python3 test_circuit_breaker.py
```

**Expected behavior:**
1. First failure → recorded, retry allowed
2. Second failure → recorded, circuit breaker trips
3. User sees clear error message
4. No third attempt

---

## 📝 Summary

**Circuit Breaker = Safety Net**

- ✅ **2 failures max** per worker
- ✅ **Automatic detection** of errors
- ✅ **Clear user feedback** when limit hit
- ✅ **System-wide enforcement** in all supervisors
- ✅ **Configurable limit** via constant

**Result:** No more infinite loops! 🎉

---

**Implementation Date:** 2025-10-31  
**Commit:** `54619a8`  
**Branch:** `dev`  
**Status:** ✅ Active on dev deployment
