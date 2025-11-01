# 🏗️ Swarm-as-Code - Declarative Agent Configuration

## 🎯 Philosophy

**Decouple configuration from code** - like Infrastructure-as-Code (IaC), but for agent swarms.

- ✅ **Agents defined in YAML** - no Python code changes needed
- ✅ **Prompts in Markdown files** - non-engineers can edit
- ✅ **Dynamic loading** - runtime builds swarm from config
- ✅ **Version control** - track swarm evolution in Git
- ✅ **A/B testing** - easily swap configurations
- ✅ **CEO-friendly** - modify agent behavior without touching code

---

## 📁 Directory Structure

```
swarm_config/
├── swarm.yaml                    # Root swarm architecture
├── agents/                       # Individual agent configs
│   ├── recipe_agent.yaml
│   ├── team_pm_agent.yaml
│   └── visualization_agent.yaml
├── supervisors/                  # Supervisor configs
│   ├── root_supervisor.yaml
│   ├── chef_supervisor.yaml
│   └── kitchen_supervisor.yaml
└── prompts/                      # Externalized prompts
    ├── agents/
    │   ├── recipe_agent.md
    │   └── team_pm_agent.md
    └── supervisors/
        ├── root_supervisor.md
        └── kitchen_supervisor.md
```

---

## 🚀 Quick Start

### **Load Swarm from Config:**

```python
from swarm_loader import load_swarm

# Load entire swarm from YAML
agent = load_swarm("swarm_config/swarm.yaml")

# Use it
result = agent.invoke({"messages": [HumanMessage(content="get recipe")]})
```

That's it! No hard-coded agent definitions needed.

---

## 📝 Configuration Files

### **1. Swarm Architecture (swarm.yaml)**

Defines the **entire hierarchy** in one place:

```yaml
name: ROA
version: "2.0"

hierarchy:
  root:
    type: supervisor
    config: supervisors/root_supervisor.yaml
    
    children:
      chef_team:
        type: supervisor
        config: supervisors/chef_supervisor.yaml
        
        children:
          kitchen_team:
            type: supervisor
            config: supervisors/kitchen_supervisor.yaml
            
            children:
              recipe:
                type: worker
                config: agents/recipe_agent.yaml
```

**Benefits:**
- See entire swarm structure at a glance
- Easy to reorganize hierarchy
- Version control tracks architectural changes

---

### **2. Agent Config (agents/recipe_agent.yaml)**

Defines a **worker agent**:

```yaml
name: recipe_agent
type: worker
team: kitchen_team

description: |
  Recipe database specialist with Neo4j access

system_prompt_file: prompts/agents/recipe_agent.md

tools:
  - search_recipes
  - get_recipe_details

config:
  max_loops: 3
  verbose: true
  retry_attempts: 2

capabilities:
  - Search recipes by name
  - Get detailed recipe info

limitations:
  - Cannot list kitchens
  - Cannot modify recipes
```

**Benefits:**
- Self-documenting (capabilities, limitations)
- Easy to add/remove tools
- Configuration separate from behavior

---

### **3. Supervisor Config (supervisors/kitchen_supervisor.yaml)**

Defines a **supervisor**:

```yaml
name: kitchen_supervisor
type: supervisor

system_prompt_file: prompts/supervisors/kitchen_supervisor.md

workers:
  - name: recipe
    agent_config: agents/recipe_agent.yaml
    
  - name: team_pm
    agent_config: agents/team_pm_agent.yaml

routing_strategy: tool_visibility
routing_config:
  max_same_worker_attempts: 2
  max_total_attempts: 3
  show_tool_table: true
```

**Benefits:**
- Routing logic externalized
- Easy to add new workers
- Circuit breaker configurable per supervisor

---

### **4. System Prompt (prompts/agents/recipe_agent.md)**

Prompts in **Markdown** for easy editing:

```markdown
# Recipe Agent System Prompt

You are a recipe database specialist.

## Your Role
Search and retrieve recipes from Neo4j.

## Available Tools
- search_recipes(kitchen_name?, recipe_name?)
- get_recipe_details(recipe_name)

## Rules
1. ONLY handle recipe operations
2. NEVER make up recipes
3. Handle typos gracefully
```

**Benefits:**
- Non-engineers can edit
- Markdown formatting (readable)
- Version control tracks prompt evolution
- Easy A/B testing

---

## 🎨 Adding a New Agent (No Code!)

### **Scenario: CEO wants to add a "marketing_agent"**

**Step 1: Create agent config**

```yaml
# swarm_config/agents/marketing_agent.yaml
name: marketing_agent
type: worker
team: marketing_team

system_prompt_file: prompts/agents/marketing_agent.md

tools:
  - create_marketing_content

config:
  max_loops: 1
  verbose: false
```

**Step 2: Create prompt**

```markdown
# swarm_config/prompts/agents/marketing_agent.md

You are a marketing content creator.

Create engaging promotional copy for culinary products.
```

**Step 3: Add to hierarchy**

```yaml
# In swarm.yaml, add under root:
hierarchy:
  root:
    children:
      marketing:
        type: worker
        config: agents/marketing_agent.yaml
```

**Step 4: Register tool** (only code change needed)

```yaml
# In swarm.yaml tools section:
tools:
  create_marketing_content:
    module: agent
    function: create_marketing_content
```

**That's it!** No Python code changes to `agent.py`.

---

## 🔄 Dynamic Swarm Evolution

### **Scenario: CEO wants to test new prompt for recipe agent**

**Without Swarm-as-Code:**
```python
# Edit agent.py line 698
recipe_agent = create_react_agent(
    llm, 
    [search_recipes],
    prompt="""New prompt here..."""  # ❌ Hard-coded
)
```
- Must redeploy entire agent.py
- Code review required
- High friction for experimentation

**With Swarm-as-Code:**
```bash
# Edit the markdown file
vim swarm_config/prompts/agents/recipe_agent.md

# Commit
git commit -m "Experiment: More conservative recipe agent"
git push origin experiment/conservative-recipe

# Deploy just the config
# Agent loads new prompt automatically
```
- ✅ No code changes
- ✅ Fast iteration
- ✅ Easy rollback (`git revert`)

---

## 🧪 A/B Testing Swarm Configs

### **Test two different architectures:**

```python
# Production config
prod_swarm = load_swarm("swarm_config/swarm.yaml")

# Experimental config (different hierarchy)
exp_swarm = load_swarm("swarm_config/swarm_experimental.yaml")

# Route 10% traffic to experiment
if random.random() < 0.1:
    result = exp_swarm.invoke(request)
else:
    result = prod_swarm.invoke(request)
```

---

## 📊 Benefits

### **1. CEO Can Iterate Independently**
- Edit prompts in Markdown
- Tweak circuit breaker limits
- Add/remove agents
- No waiting for engineering

### **2. Version Control = Time Machine**
```bash
# See swarm evolution
git log swarm_config/

# Rollback to last week
git checkout HEAD~7 swarm_config/

# Compare prompts
git diff main experiment -- swarm_config/prompts/
```

### **3. Environment-Specific Configs**
```
swarm_config/
├── swarm.production.yaml   # Conservative, stable
├── swarm.staging.yaml      # Latest features
└── swarm.dev.yaml          # Experimental
```

### **4. Documentation Built-In**
YAML configs are **self-documenting**:
```yaml
capabilities:
  - Search recipes
limitations:
  - Cannot list kitchens  # ← Clear limitation
examples:
  - input: "get recipe"
    expected_tool: search_recipes
```

---

## 🛠️ Tool Registry

Tools are **referenced by name** in YAML, **implemented once** in Python:

```yaml
# swarm.yaml
tools:
  search_recipes:
    module: src.teams.chef.kitchen.tools
    function: search_recipes
```

```python
# src/teams/chef/kitchen/tools.py
@tool
def search_recipes(kitchen_name: str) -> str:
    """Search recipes..."""
    # Implementation
```

**SwarmLoader** dynamically imports tools at runtime.

---

## 🎯 Best Practices

### **1. Prompt Files = Single Source of Truth**
- ❌ Don't: Embed prompts in both YAML and Python
- ✅ Do: Reference prompt file in YAML, content in `.md`

### **2. Version Your Configs**
```bash
git tag -a v2.0-swarm -m "Swarm-as-Code architecture"
```

### **3. Document Limitations**
```yaml
limitations:
  - Cannot list kitchens  # Issue #42
  - No recipe creation    # Feature planned Q1 2026
```

### **4. Test Configs Locally**
```python
# tests/test_swarm_config.py
def test_swarm_loads():
    swarm = load_swarm("swarm_config/swarm.yaml")
    assert swarm is not None
```

---

## 🚀 Migration Path

### **Phase 1: Externalize Prompts** ✅ (Do this first)
```python
# Before
prompt = "You are a recipe agent..."

# After
prompt = load_prompt("agents/recipe_agent.md")
```

### **Phase 2: Agent Configs** (Current)
```yaml
# agents/recipe_agent.yaml
tools: [search_recipes]
```

### **Phase 3: Full Swarm YAML** (Future)
```python
# agent.py becomes 3 lines:
from swarm_loader import load_swarm
agent = load_swarm()
```

---

## 📈 Metrics to Track

After implementing Swarm-as-Code:

- ⏱️ **Time to modify agent** (should decrease from hours → minutes)
- 🔄 **Iteration frequency** (should increase)
- 🐛 **Config-related bugs** (should decrease - YAML validates)
- 📝 **Non-engineer contributions** (CEO can now edit prompts!)

---

## ✅ Summary

**Before (Code-Heavy):**
```python
# agent.py (500+ lines of hard-coded agents)
recipe_agent = create_react_agent(llm, [tool1, tool2], prompt="...")
kitchen_supervisor = make_supervisor_node(llm, ["recipe", ...])
...
```
- ❌ Hard to modify
- ❌ Requires code review
- ❌ CEO can't iterate

**After (Config-Driven):**
```python
# agent.py (3 lines)
from swarm_loader import load_swarm
agent = load_swarm("swarm_config/swarm.yaml")
```

```yaml
# swarm_config/ (readable YAML + Markdown)
hierarchy: ...
tools: ...
```
- ✅ Easy to modify
- ✅ Git tracks changes
- ✅ CEO can iterate independently

**Result: Swarm becomes evolutionary, not static!** 🧬

---

**Implementation Status:** Ready for Phase 1-2  
**Next:** Migrate existing agents to YAML configs  
**Author:** ROA Team  
**Date:** 2025-11-01
