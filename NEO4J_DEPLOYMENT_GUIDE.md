# Neo4j-Based Agent Swarm Deployment Guide

**Version:** 1.0  
**Status:** Ready for Testing  
**Architecture:** Multi-Tenant, Marketplace-Ready, Dynamically Loaded

---

## 🎯 **What We Built**

A **Neo4j-powered agent management system** that:

1. ✅ Stores agent definitions, prompts, tools, and hierarchy in Neo4j
2. ✅ Builds LangGraph swarms dynamically at runtime
3. ✅ Supports multi-tenancy (different restaurants = different agent configs)
4. ✅ Ready for marketplace (install agents without code deployment)
5. ✅ Scales to 100+ agents with queryable relationships

---

## 📁 **Files Created**

```
agent/
├── NEO4J_AGENT_SCHEMA.md      # Database schema design
├── meta_swarm.py               # Dynamic graph loader from Neo4j
├── migrate_to_neo4j.py         # Migration script (swarm.py → Neo4j)
├── test_meta_swarm.py          # Testing script
└── NEO4J_DEPLOYMENT_GUIDE.md   # This file
```

---

## 🚀 **Quick Start (Local Testing)**

### **Step 1: Ensure Neo4j is Running**

```bash
# Check your Neo4j is accessible
echo $NEO4J_URI
# Should output something like: neo4j://localhost:7687 or neo4j+s://xxx.databases.neo4j.io
```

### **Step 2: Run Migration**

Populate Neo4j with your agent definitions:

```bash
cd /home/yotambg/Documents/foodie-stuff/roa-voice/agent

# Migrate for default tenant
python3 migrate_to_neo4j.py --tenant-id default --clear

# Output:
# 🚀 NEO4J AGENT MIGRATION
# ══════════════════════════════════════════════════════════════════════
# Tenant: default
# 📊 Creating indexes...
# ✅ Indexes created
# 🗑️  Clearing existing data for tenant: default
# ✅ Existing data cleared
# 🏢 Creating tenant: default
# ✅ Tenant created
# 🔧 Creating 16 tools...
# ✅ Created 16 tools
# 👥 Creating 16 agents...
# ✅ Created 16 agents
# 🔗 Creating relationships...
# ✅ All relationships created
# 🔍 Verifying migration...
#    Agents: 16/16 ✅
#    Tools: 16/16 ✅
#    ...
# 🎉 MIGRATION COMPLETE!
```

### **Step 3: Test Loading**

```bash
python3 test_meta_swarm.py

# Output:
# 🧪 Testing Meta-Swarm (Neo4j-based)
# ══════════════════════════════════════════════════════════════════════
# 📦 TEST 1: Import meta_swarm module
# ✅ Import successful
# 📦 TEST 2: Load swarm from Neo4j
# 🚀 Loading swarm from Neo4j for tenant: default
#    Found 16 agents
#    Root supervisor: root_supervisor
# ✅ Swarm built successfully!
#    Nodes: ['__start__', 'supervisor', 'visualization', 'marketing', 'builder_team', 'chef_team']
# ...
# 🎉 META-SWARM TESTING COMPLETE!
```

### **Step 4: Verify in Neo4j Browser**

Open Neo4j Browser and run:

```cypher
// View full agent hierarchy
MATCH (t:Tenant {id: 'default'})<-[:BELONGS_TO]-(a:Agent)
OPTIONAL MATCH (a)-[:SUPERVISES]->(child:Agent)
OPTIONAL MATCH (a)-[:HAS_TOOL]->(tool:Tool)
RETURN t, a, child, tool
LIMIT 100
```

You should see a beautiful graph visualization of your swarm!

---

## 🌐 **Deploy to LangGraph Cloud**

### **Option A: Use meta_swarm.py (Recommended)**

Update `langgraph.json`:

```json
{
  "dependencies": ["."],
  "graphs": {
    "agent": "./meta_swarm.py:agent"
  },
  "env": ".env",
  "python_version": "3.11"
}
```

**Pros:**
- ✅ Loads from Neo4j at startup
- ✅ Edit agents in DB → restart → changes live
- ✅ Multi-tenant ready

**Cons:**
- ⚠️ Requires Neo4j connection at startup (~200ms)
- ⚠️ If Neo4j is down, agent won't start

---

### **Option B: Keep swarm.py as Fallback**

Keep both files, use env var to choose:

```python
# In your deployment entry point
import os

if os.getenv("USE_NEO4J_SWARM", "false") == "true":
    from meta_swarm import agent
else:
    from swarm import agent
```

**Pros:**
- ✅ Gradual migration
- ✅ Fallback if Neo4j issues

**Cons:**
- ⚠️ Two systems to maintain

---

## 🏢 **Multi-Tenant Deployment**

### **Add New Restaurant/Tenant**

```bash
# Create tenant "Chez Pierre"
python3 migrate_to_neo4j.py \
  --tenant-id restaurant_pierre \
  --tenant-name "Chez Pierre" \
  --clear

# Now load their swarm
python3 -c "
from meta_swarm import load_swarm_from_neo4j
agent = load_swarm_from_neo4j('restaurant_pierre')
print('Loaded Chez Pierre swarm:', list(agent.nodes.keys()))
"
```

### **API with Multi-Tenant Routing**

```python
# In your Flask/FastAPI server
from meta_swarm import get_swarm

@app.post("/chat")
def chat(tenant_id: str, message: str):
    # Each tenant gets their own swarm from Neo4j
    swarm = get_swarm(tenant_id)
    result = swarm.invoke({"messages": [{"role": "user", "content": message}]})
    return result
```

---

## 🛍️ **Marketplace Implementation**

### **Install Agent Package**

```python
def install_marketplace_agent(tenant_id: str, package_id: str):
    """Install agent from marketplace"""
    from neo4j import GraphDatabase
    import uuid
    
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    with driver.session() as session:
        # Get package from marketplace
        package = marketplace_api.get_package(package_id)
        
        # Create agent in Neo4j
        session.run("""
            CREATE (a:Agent {
                id: $id,
                name: $name,
                type: 'worker',
                prompt: $prompt,
                tenant_id: $tenant_id,
                enabled: true,
                created_at: timestamp()
            })
            CREATE (a)-[:INSTALLED_FROM]->(:MarketplacePackage {
                id: $package_id,
                version: $version
            })
        """, {
            "id": str(uuid.uuid4()),
            "name": package.name,
            "prompt": package.prompt,
            "tenant_id": tenant_id,
            "package_id": package_id,
            "version": package.version
        })
        
        # Create tools
        for tool in package.tools:
            session.run("""
                MATCH (a:Agent {name: $agent_name, tenant_id: $tenant_id})
                CREATE (t:Tool {id: $tool_id, name: $tool_name, ...})
                CREATE (a)-[:HAS_TOOL]->(t)
            """, ...)
        
        # Wire into hierarchy
        session.run("""
            MATCH (parent:Agent {name: $parent_name, tenant_id: $tenant_id})
            MATCH (child:Agent {name: $agent_name, tenant_id: $tenant_id})
            CREATE (parent)-[:SUPERVISES]->(child)
        """, ...)
    
    # Invalidate cache so next request rebuilds swarm
    from meta_swarm import invalidate_tenant_cache
    invalidate_tenant_cache(tenant_id)
```

---

## 🔄 **Update Agent Prompts (Without Deployment)**

### **Method 1: Direct Cypher Update**

```cypher
// Update recipe agent prompt
MATCH (a:Agent {name: 'recipe', tenant_id: 'default'})
SET a.prompt = 'NEW PROMPT: You are a recipe specialist...',
    a.updated_at = timestamp(),
    a.version = '1.1.0'
RETURN a
```

Then restart or invalidate cache:

```python
from meta_swarm import invalidate_tenant_cache
invalidate_tenant_cache('default')
```

### **Method 2: API Endpoint**

```python
@app.post("/admin/agents/{agent_name}/prompt")
def update_agent_prompt(agent_name: str, tenant_id: str, new_prompt: str):
    """Update agent prompt without redeployment"""
    from neo4j import GraphDatabase
    
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    with driver.session() as session:
        # Save old version
        session.run("""
            MATCH (a:Agent {name: $name, tenant_id: $tenant_id})
            CREATE (a)-[:HAS_PROMPT_VERSION {
                version: a.version,
                created_at: timestamp(),
                prompt_text: a.prompt
            }]->(:PromptVersion)
        """, {"name": agent_name, "tenant_id": tenant_id})
        
        # Update to new
        session.run("""
            MATCH (a:Agent {name: $name, tenant_id: $tenant_id})
            SET a.prompt = $new_prompt,
                a.updated_at = timestamp(),
                a.version = $new_version
        """, {
            "name": agent_name,
            "tenant_id": tenant_id,
            "new_prompt": new_prompt,
            "new_version": "1.1.0"  # Increment version
        })
    
    # Invalidate cache
    from meta_swarm import invalidate_tenant_cache
    invalidate_tenant_cache(tenant_id)
    
    return {"status": "success", "message": f"Updated {agent_name} prompt"}
```

---

## 📊 **Monitoring & Analytics**

### **Agent Usage Tracking**

```cypher
// Track which agents are used most
MATCH (a:Agent {tenant_id: 'default'})
SET a.invocation_count = coalesce(a.invocation_count, 0) + 1,
    a.last_used = timestamp()
RETURN a.name, a.invocation_count
ORDER BY a.invocation_count DESC
```

### **Find Performance Bottlenecks**

```cypher
// Find supervisors with too many workers
MATCH (s:Agent {type: 'supervisor', tenant_id: 'default'})-[:SUPERVISES]->(workers)
WITH s, count(workers) as num_workers
WHERE num_workers > 10
RETURN s.name, num_workers
ORDER BY num_workers DESC
```

### **Audit Trail**

```cypher
// See all prompt changes
MATCH (a:Agent {name: 'recipe', tenant_id: 'default'})
      -[:HAS_PROMPT_VERSION]->(v:PromptVersion)
RETURN v.version, v.created_at, v.prompt_text
ORDER BY v.created_at DESC
```

---

## 🔒 **Security Considerations**

### **1. Tenant Isolation**

Always filter by `tenant_id` in queries:

```cypher
// ✅ GOOD - Tenant isolated
MATCH (a:Agent {tenant_id: $tenant_id})

// ❌ BAD - Leaks across tenants
MATCH (a:Agent)
```

### **2. Input Validation**

Sanitize tenant_id before queries:

```python
import re

def validate_tenant_id(tenant_id: str):
    if not re.match(r'^[a-zA-Z0-9_-]+$', tenant_id):
        raise ValueError("Invalid tenant_id")
    return tenant_id
```

### **3. Neo4j Permissions**

Use read-only user for swarm loading:

```cypher
// Create read-only user
CREATE USER swarm_reader SET PASSWORD 'secure_password';
GRANT TRAVERSE ON GRAPH * NODES * TO swarm_reader;
GRANT READ {*} ON GRAPH * NODES * TO swarm_reader;
```

---

## 🐛 **Troubleshooting**

### **Issue: "No agents found for tenant"**

```bash
# Check if tenant exists
python3 -c "
from neo4j import GraphDatabase
driver = GraphDatabase.driver('$NEO4J_URI', auth=('$NEO4J_USER', '$NEO4J_PASSWORD'))
with driver.session() as session:
    result = session.run('MATCH (a:Agent {tenant_id: \$tid}) RETURN count(a) as count', tid='default')
    print(f'Agents found: {result.single()[\"count\"]}')
"

# If 0, run migration:
python3 migrate_to_neo4j.py --tenant-id default --clear
```

### **Issue: "Tool 'xyz' not found"**

```bash
# Check if tools are in Neo4j
python3 -c "
from neo4j import GraphDatabase
driver = GraphDatabase.driver('$NEO4J_URI', auth=('$NEO4J_USER', '$NEO4J_PASSWORD'))
with driver.session() as session:
    result = session.run('MATCH (t:Tool) RETURN t.name as name')
    tools = [r['name'] for r in result]
    print(f'Tools in Neo4j: {tools}')
"
```

### **Issue: Cache not invalidating**

```python
# Force clear all tenant caches
from meta_swarm import _TENANT_SWARMS
_TENANT_SWARMS.clear()
```

---

## 📈 **Performance Optimization**

### **1. Connection Pooling**

```python
# In meta_swarm.py, use singleton driver
_NEO4J_DRIVER = None

def get_driver():
    global _NEO4J_DRIVER
    if _NEO4J_DRIVER is None:
        _NEO4J_DRIVER = GraphDatabase.driver(NEO4J_URI, auth=(USER, PASS))
    return _NEO4J_DRIVER
```

### **2. Query Optimization**

Add indexes (already in migrate_to_neo4j.py):

```cypher
CREATE INDEX agent_tenant_name IF NOT EXISTS 
FOR (a:Agent) ON (a.tenant_id, a.name);
```

### **3. Caching Strategy**

```python
# Cache swarms by tenant
# Invalidate only on agent updates
# TTL: 1 hour (for prompt changes to take effect)
```

---

## 🎯 **Next Steps**

### **Phase 1: Testing (This Week)**
- [x] Local testing with default tenant
- [ ] Deploy to staging with Neo4j
- [ ] Test multi-tenant with 2-3 test restaurants
- [ ] Benchmark performance vs swarm.py

### **Phase 2: Production (Next Week)**
- [ ] Deploy to production
- [ ] Monitor for issues
- [ ] Build admin UI for prompt editing
- [ ] Add analytics dashboard

### **Phase 3: Marketplace (Month 2)**
- [ ] Design agent package format
- [ ] Build installation API
- [ ] Create marketplace UI
- [ ] Beta test with first marketplace agents

### **Phase 4: Scale (Month 3+)**
- [ ] Add more tenants
- [ ] Optimize query performance
- [ ] Build hierarchical visualization
- [ ] A/B testing framework

---

## 📞 **Support**

**Issues?** Check:
1. Neo4j connection (neo4j+s:// not neo4j://)
2. Environment variables set correctly
3. Migration ran successfully
4. Indexes created

**Still stuck?** Review logs and test with:
```bash
python3 test_meta_swarm.py
```

---

**Status:** ✅ Ready for Testing  
**Architecture:** Multi-Tenant, Marketplace-Ready, Production-Grade  
**Next:** Deploy and test with real traffic! 🚀
