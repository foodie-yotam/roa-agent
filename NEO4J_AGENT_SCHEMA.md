# Neo4j Agent Swarm Schema

**Purpose:** Store agent definitions, tools, hierarchy, and marketplace metadata in Neo4j for dynamic multi-tenant swarm building.

---

## 🎯 **Core Concepts**

1. **Agents** = Nodes that process tasks (workers or supervisors)
2. **Tools** = Functions agents can call
3. **Hierarchy** = Supervision relationships (who delegates to whom)
4. **Tenants** = Restaurants/customers with isolated agent configs
5. **Marketplace** = Installable agent packages

---

## 📊 **Node Labels**

### **`:Agent`**
Represents an agent in the swarm (worker or supervisor).

```cypher
(:Agent {
  id: "uuid-123",                    // Unique identifier
  name: "recipe_agent",              // Agent name (unique per tenant)
  type: "worker",                    // "worker" or "supervisor"
  prompt: "You are a recipe...",     // System prompt (can be large)
  tenant_id: "restaurant_abc",       // Multi-tenant isolation
  enabled: true,                     // Can be disabled without deletion
  version: "1.2.0",                  // Agent version
  created_at: 1730505600000,         // Timestamp
  updated_at: 1730505600000,         // Last modified
  metadata: {                        // Flexible JSON field
    description: "Recipe specialist",
    tags: ["kitchen", "core"],
    max_loops: 3
  }
})
```

### **`:Tool`**
Represents a callable function/tool.

```cypher
(:Tool {
  id: "uuid-456",
  name: "search_recipes",            // Tool name
  module: "agent",                   // Python module path
  function: "search_recipes",        // Function name
  description: "Search recipes in Neo4j",
  tenant_id: "restaurant_abc",       // Can be tenant-specific or global
  is_global: true,                   // Available to all tenants?
  created_at: 1730505600000
})
```

### **`:MarketplacePackage`**
Installable agent from marketplace.

```cypher
(:MarketplacePackage {
  id: "uuid-789",
  name: "Wine Pairing Pro",
  version: "2.1.0",
  author: "SommelierAI",
  description: "Suggests wine pairings",
  price: 49.00,                      // Monthly price in USD
  category: "kitchen",
  rating: 4.8,
  installs: 142,
  published_at: 1730505600000,
  manifest: {                        // Package definition
    agents: [{...}],
    tools: [{...}]
  }
})
```

### **`:Tenant`**
Restaurant/customer account.

```cypher
(:Tenant {
  id: "restaurant_abc",
  name: "Chez Pierre",
  type: "fine_dining",               // Restaurant type
  plan: "pro",                       // Pricing tier
  created_at: 1730505600000,
  settings: {
    max_agents: 50,
    features: ["marketplace", "custom_agents"]
  }
})
```

---

## 🔗 **Relationships**

### **`[:SUPERVISES]`**
Supervisor → Worker delegation.

```cypher
(:Agent {type: "supervisor"})-[:SUPERVISES {
  priority: 1,                       // Routing priority
  can_retry: true,                   // Allow retry on failure?
  max_retries: 2
}]->(:Agent {type: "worker"})
```

### **`[:HAS_TOOL]`**
Agent can use this tool.

```cypher
(:Agent)-[:HAS_TOOL]->(:Tool)
```

### **`[:BELONGS_TO]`**
Agent/Tool belongs to tenant.

```cypher
(:Agent)-[:BELONGS_TO]->(:Tenant)
(:Tool)-[:BELONGS_TO]->(:Tenant)
```

### **`[:INSTALLED_FROM]`**
Agent was installed from marketplace package.

```cypher
(:Agent)-[:INSTALLED_FROM {
  installed_at: 1730505600000,
  installed_by: "user_123"
}]->(:MarketplacePackage)
```

### **`[:DEPENDS_ON]`**
Agent requires another agent to function.

```cypher
(:Agent)-[:DEPENDS_ON]->(:Agent)
```

### **`[:HAS_PROMPT_VERSION]`**
Historical prompt versions (for rollback).

```cypher
(:Agent)-[:HAS_PROMPT_VERSION {
  version: "1.1.0",
  created_at: 1730505600000,
  prompt_text: "Old prompt...",
  created_by: "user_123"
}]->(:PromptVersion)
```

---

## 📋 **Example: Complete Hierarchy**

```cypher
// Tenant
(tenant:Tenant {id: "restaurant_abc", name: "Chez Pierre"})

// Root supervisor
(root:Agent {
  name: "root_supervisor",
  type: "supervisor",
  tenant_id: "restaurant_abc"
})-[:BELONGS_TO]->(tenant)

// Kitchen supervisor
(kitchen:Agent {
  name: "kitchen_supervisor",
  type: "supervisor",
  tenant_id: "restaurant_abc"
})-[:BELONGS_TO]->(tenant)

(root)-[:SUPERVISES {priority: 1}]->(kitchen)

// Recipe worker
(recipe:Agent {
  name: "recipe_agent",
  type: "worker",
  prompt: "You are a recipe specialist...",
  tenant_id: "restaurant_abc"
})-[:BELONGS_TO]->(tenant)

(kitchen)-[:SUPERVISES {priority: 1}]->(recipe)

// Tools
(search_tool:Tool {name: "search_recipes"})-[:BELONGS_TO]->(tenant)
(details_tool:Tool {name: "get_recipe_details"})-[:BELONGS_TO]->(tenant)

(recipe)-[:HAS_TOOL]->(search_tool)
(recipe)-[:HAS_TOOL]->(details_tool)
```

---

## 🔍 **Key Queries**

### **Load All Agents for Tenant**
```cypher
MATCH (a:Agent {tenant_id: $tenant_id, enabled: true})
OPTIONAL MATCH (a)-[:HAS_TOOL]->(t:Tool)
OPTIONAL MATCH (parent)-[:SUPERVISES]->(a)
RETURN a, collect(DISTINCT t) as tools, parent
ORDER BY 
  CASE a.type 
    WHEN 'supervisor' THEN 0 
    ELSE 1 
  END,
  a.name
```

### **Get Agent Hierarchy**
```cypher
MATCH path = (root:Agent {name: "root_supervisor", tenant_id: $tenant_id})
             -[:SUPERVISES*]->(child:Agent)
RETURN path
```

### **Find Agents with Specific Tool**
```cypher
MATCH (a:Agent)-[:HAS_TOOL]->(t:Tool {name: $tool_name})
WHERE a.tenant_id = $tenant_id
RETURN a
```

### **Install Marketplace Package**
```cypher
// 1. Get package
MATCH (pkg:MarketplacePackage {id: $package_id})

// 2. Create agents from manifest
UNWIND pkg.manifest.agents as agent_def
CREATE (a:Agent {
  id: randomUUID(),
  name: agent_def.name,
  type: agent_def.type,
  prompt: agent_def.prompt,
  tenant_id: $tenant_id,
  enabled: true,
  created_at: timestamp()
})
CREATE (a)-[:INSTALLED_FROM {installed_at: timestamp()}]->(pkg)

// 3. Wire up tools and hierarchy
// (See migrate_to_neo4j.py for full logic)
```

### **Get Tenant's Installed Packages**
```cypher
MATCH (t:Tenant {id: $tenant_id})<-[:BELONGS_TO]-(a:Agent)
      -[:INSTALLED_FROM]->(pkg:MarketplacePackage)
RETURN DISTINCT pkg
```

---

## 🎨 **Visualization**

In Neo4j Browser, run:
```cypher
MATCH path = (t:Tenant {id: "restaurant_abc"})<-[:BELONGS_TO]-
             (a:Agent)-[:SUPERVISES*0..]->(child)
OPTIONAL MATCH (a)-[:HAS_TOOL]->(tool:Tool)
RETURN path, tool
LIMIT 100
```

Creates a beautiful graph showing:
- 🏢 Tenant at center
- 👔 Supervisors (purple)
- 👨‍🍳 Workers (blue)
- 🔧 Tools (green)
- ➡️ Supervision paths

---

## 🔐 **Indexes (Performance)**

```cypher
// Required indexes
CREATE INDEX agent_tenant_name IF NOT EXISTS
FOR (a:Agent) ON (a.tenant_id, a.name);

CREATE INDEX agent_tenant_enabled IF NOT EXISTS
FOR (a:Agent) ON (a.tenant_id, a.enabled);

CREATE CONSTRAINT agent_id_unique IF NOT EXISTS
FOR (a:Agent) REQUIRE a.id IS UNIQUE;

CREATE INDEX tool_name IF NOT EXISTS
FOR (t:Tool) ON (t.name);

CREATE INDEX tenant_id IF NOT EXISTS
FOR (t:Tenant) ON (t.id);
```

---

## 🚀 **Migration Strategy**

1. **Phase 1:** Run migration script → populate Neo4j from `swarm.py`
2. **Phase 2:** Test `meta_swarm.py` alongside existing `agent.py`
3. **Phase 3:** Switch deployment to use `meta_swarm.py`
4. **Phase 4:** Add marketplace capabilities
5. **Phase 5:** Add multi-tenancy

---

## 📦 **Python Data Models**

```python
from dataclasses import dataclass
from typing import List, Dict, Optional

@dataclass
class AgentNode:
    id: str
    name: str
    type: str  # "worker" or "supervisor"
    prompt: str
    tenant_id: str
    enabled: bool = True
    version: str = "1.0.0"
    metadata: Dict = None

@dataclass
class ToolNode:
    id: str
    name: str
    module: str
    function: str
    tenant_id: str
    is_global: bool = True

@dataclass
class Relationship:
    from_id: str
    to_id: str
    type: str
    properties: Dict = None
```

---

## 🎯 **Next Steps**

- [x] Design schema
- [ ] Implement `meta_swarm.py`
- [ ] Create migration script
- [ ] Test on single tenant
- [ ] Add multi-tenant support
- [ ] Build marketplace API
