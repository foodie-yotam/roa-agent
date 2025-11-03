#!/usr/bin/env python3
"""
Migration Script: Populate Neo4j with Agent Definitions

Reads the current agent configuration from swarm.py and populates
Neo4j with the agent hierarchy, prompts, and tools.

Usage:
    python3 migrate_to_neo4j.py --tenant-id default
    python3 migrate_to_neo4j.py --tenant-id restaurant_abc --clear
"""

import os
import sys
import argparse
import uuid
from datetime import datetime
from neo4j import GraphDatabase


# ============================================================================
# AGENT CONFIGURATION (from swarm.py)
# ============================================================================

AGENTS = {
    "visualization": {
        "type": "worker",
        "prompt": """You are a visualization specialist for kitchen operations.
Create visual displays when users need to SEE data graphically.
ONLY create visualizations when explicitly requested or clearly beneficial.""",
        "tools": ["display_recipes", "display_multiplication", "display_prediction_graph", 
                 "display_inventory_alert", "display_team_assignment"],
        "parent": "root_supervisor",
        "description": "Creates visual displays for kitchen data"
    },
    
    "marketing": {
        "type": "worker",
        "prompt": """You are a marketing content creator for culinary products.
Generate marketing copy and promotional content.
ONLY handle marketing/promotional content requests.""",
        "tools": ["create_marketing_content"],
        "parent": "root_supervisor",
        "description": "Generates marketing content"
    },
    
    "dev_tools": {
        "type": "worker",
        "prompt": """You are a developer tool assistant.
Generate Python code for tools and scripts.
ONLY handle code generation requests.""",
        "tools": ["generate_tool_code"],
        "parent": "builder_supervisor",
        "description": "Generates code and tools"
    },
    
    "recipe": {
        "type": "worker",
        "prompt": """You are a recipe database specialist with access to Neo4j database.
Search and retrieve recipe information from Neo4j.
ONLY handle recipe operations - NOT inventory, team, or sales.""",
        "tools": ["search_recipes", "get_recipe_details"],
        "parent": "kitchen_supervisor",
        "description": "Recipe database specialist"
    },
    
    "team_pm": {
        "type": "worker",
        "prompt": """You are a team project manager.
Manage team members, tasks, and assignments.
ONLY handle team management operations.""",
        "tools": ["get_team_members", "assign_task"],
        "parent": "kitchen_supervisor",
        "description": "Team management specialist"
    },
    
    "dish_ideation": {
        "type": "worker",
        "prompt": """You are a dish ideation specialist.
Suggest dish ideas based on ingredients.
ONLY handle dish ideation requests.""",
        "tools": ["suggest_dishes"],
        "parent": "kitchen_supervisor",
        "description": "Dish ideation specialist"
    },
    
    "stock": {
        "type": "worker",
        "prompt": """You are an inventory management specialist.
Check stock levels and manage inventory.
ONLY handle inventory management operations.""",
        "tools": ["check_stock"],
        "parent": "inventory_supervisor",
        "description": "Stock management specialist"
    },
    
    "suppliers": {
        "type": "worker",
        "prompt": """You are a supplier management specialist.
Manage suppliers and their information.
ONLY handle supplier management operations.""",
        "tools": ["list_suppliers"],
        "parent": "inventory_supervisor",
        "description": "Supplier management specialist"
    },
    
    "analysis": {
        "type": "worker",
        "prompt": """You are a demand forecasting specialist.
Forecast demand for items.
ONLY handle demand forecasting operations.""",
        "tools": ["forecast_demand"],
        "parent": "inventory_supervisor",
        "description": "Demand forecasting specialist"
    },
    
    "profit": {
        "type": "worker",
        "prompt": """You are a profitability analyst.
Calculate costs and analyze profit margins.
ONLY handle cost/profit analysis operations.""",
        "tools": ["calculate_cost"],
        "parent": "sales_supervisor",
        "description": "Profitability analyst"
    },
}

SUPERVISORS = {
    "root_supervisor": {
        "type": "supervisor",
        "parent": None,  # Root
        "description": "Root supervisor coordinating all teams",
        "workers": ["visualization", "marketing", "builder_supervisor", "chef_supervisor"]
    },
    
    "builder_supervisor": {
        "type": "supervisor",
        "parent": "root_supervisor",
        "description": "Builder team supervisor",
        "workers": ["dev_tools"]
    },
    
    "chef_supervisor": {
        "type": "supervisor",
        "parent": "root_supervisor",
        "description": "Chef meta-team supervisor",
        "workers": ["kitchen_supervisor", "inventory_supervisor", "sales_supervisor"]
    },
    
    "kitchen_supervisor": {
        "type": "supervisor",
        "parent": "chef_supervisor",
        "description": "Kitchen team supervisor",
        "workers": ["recipe", "team_pm", "dish_ideation"]
    },
    
    "inventory_supervisor": {
        "type": "supervisor",
        "parent": "chef_supervisor",
        "description": "Inventory team supervisor",
        "workers": ["stock", "suppliers", "analysis"]
    },
    
    "sales_supervisor": {
        "type": "supervisor",
        "parent": "chef_supervisor",
        "description": "Sales team supervisor",
        "workers": ["profit"]
    },
}

TOOLS = {
    "search_recipes": {"module": "agent", "function": "search_recipes"},
    "get_recipe_details": {"module": "agent", "function": "get_recipe_details"},
    "get_team_members": {"module": "agent", "function": "get_team_members"},
    "assign_task": {"module": "agent", "function": "assign_task"},
    "suggest_dishes": {"module": "agent", "function": "suggest_dishes"},
    "check_stock": {"module": "agent", "function": "check_stock"},
    "list_suppliers": {"module": "agent", "function": "list_suppliers"},
    "forecast_demand": {"module": "agent", "function": "forecast_demand"},
    "calculate_cost": {"module": "agent", "function": "calculate_cost"},
    "display_recipes": {"module": "agent", "function": "display_recipes"},
    "display_multiplication": {"module": "agent", "function": "display_multiplication"},
    "display_prediction_graph": {"module": "agent", "function": "display_prediction_graph"},
    "display_inventory_alert": {"module": "agent", "function": "display_inventory_alert"},
    "display_team_assignment": {"module": "agent", "function": "display_team_assignment"},
    "create_marketing_content": {"module": "agent", "function": "create_marketing_content"},
    "generate_tool_code": {"module": "agent", "function": "generate_tool_code"},
}


# ============================================================================
# MIGRATION CLASS
# ============================================================================

class Neo4jMigration:
    """Handles migration of agent config to Neo4j"""
    
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
    
    def close(self):
        self.driver.close()
    
    def execute(self, cypher: str, parameters: dict = None):
        """Execute Cypher query"""
        with self.driver.session() as session:
            result = session.run(cypher, parameters or {})
            return result.data()
    
    def clear_tenant_data(self, tenant_id: str):
        """Clear all existing agent data for tenant"""
        print(f"🗑️  Clearing existing data for tenant: {tenant_id}")
        
        self.execute("""
            MATCH (a:Agent {tenant_id: $tenant_id})
            DETACH DELETE a
        """, {"tenant_id": tenant_id})
        
        self.execute("""
            MATCH (t:Tool {tenant_id: $tenant_id})
            DETACH DELETE t
        """, {"tenant_id": tenant_id})
        
        print("✅ Existing data cleared")
    
    def create_indexes(self):
        """Create required indexes for performance"""
        print("📊 Creating indexes...")
        
        indexes = [
            "CREATE INDEX agent_tenant_name IF NOT EXISTS FOR (a:Agent) ON (a.tenant_id, a.name)",
            "CREATE INDEX agent_tenant_enabled IF NOT EXISTS FOR (a:Agent) ON (a.tenant_id, a.enabled)",
            "CREATE CONSTRAINT agent_id_unique IF NOT EXISTS FOR (a:Agent) REQUIRE a.id IS UNIQUE",
            "CREATE INDEX tool_name IF NOT EXISTS FOR (t:Tool) ON (t.name)",
            "CREATE INDEX tenant_id IF NOT EXISTS FOR (t:Tenant) ON (t.id)",
        ]
        
        for index_query in indexes:
            try:
                self.execute(index_query)
            except Exception as e:
                print(f"⚠️  Index creation warning: {e}")
        
        print("✅ Indexes created")
    
    def create_tenant(self, tenant_id: str, tenant_name: str = None):
        """Create or update tenant node"""
        print(f"🏢 Creating tenant: {tenant_id}")
        
        self.execute("""
            MERGE (t:Tenant {id: $tenant_id})
            ON CREATE SET 
                t.name = $tenant_name,
                t.created_at = timestamp(),
                t.plan = 'pro',
                t.settings = {max_agents: 50, features: ['marketplace', 'custom_agents']}
            ON MATCH SET
                t.updated_at = timestamp()
        """, {
            "tenant_id": tenant_id,
            "tenant_name": tenant_name or f"Tenant {tenant_id}"
        })
        
        print("✅ Tenant created")
    
    def create_tools(self, tenant_id: str):
        """Create tool nodes"""
        print(f"🔧 Creating {len(TOOLS)} tools...")
        
        for tool_name, tool_config in TOOLS.items():
            self.execute("""
                CREATE (t:Tool {
                    id: $id,
                    name: $name,
                    module: $module,
                    function: $function,
                    tenant_id: $tenant_id,
                    is_global: true,
                    created_at: timestamp()
                })
            """, {
                "id": str(uuid.uuid4()),
                "name": tool_name,
                "module": tool_config["module"],
                "function": tool_config["function"],
                "tenant_id": tenant_id
            })
        
        print(f"✅ Created {len(TOOLS)} tools")
    
    def create_agents(self, tenant_id: str):
        """Create agent nodes (workers and supervisors)"""
        total_agents = len(AGENTS) + len(SUPERVISORS)
        print(f"👥 Creating {total_agents} agents...")
        
        # Create workers
        for agent_name, agent_config in AGENTS.items():
            self.execute("""
                CREATE (a:Agent {
                    id: $id,
                    name: $name,
                    type: $type,
                    prompt: $prompt,
                    tenant_id: $tenant_id,
                    enabled: true,
                    version: '1.0.0',
                    created_at: timestamp(),
                    metadata: $metadata
                })
            """, {
                "id": str(uuid.uuid4()),
                "name": agent_name,
                "type": agent_config["type"],
                "prompt": agent_config["prompt"],
                "tenant_id": tenant_id,
                "metadata": {"description": agent_config["description"]}
            })
        
        # Create supervisors
        for supervisor_name, supervisor_config in SUPERVISORS.items():
            self.execute("""
                CREATE (a:Agent {
                    id: $id,
                    name: $name,
                    type: $type,
                    prompt: $prompt,
                    tenant_id: $tenant_id,
                    enabled: true,
                    version: '1.0.0',
                    created_at: timestamp(),
                    metadata: $metadata
                })
            """, {
                "id": str(uuid.uuid4()),
                "name": supervisor_name,
                "type": "supervisor",
                "prompt": f"You are {supervisor_config['description']}. Route requests to appropriate workers.",
                "tenant_id": tenant_id,
                "metadata": {"description": supervisor_config["description"]}
            })
        
        print(f"✅ Created {total_agents} agents")
    
    def create_relationships(self, tenant_id: str):
        """Create relationships between agents and tools"""
        print("🔗 Creating relationships...")
        
        # Agent → Tool relationships
        tool_count = 0
        for agent_name, agent_config in AGENTS.items():
            for tool_name in agent_config["tools"]:
                self.execute("""
                    MATCH (a:Agent {name: $agent_name, tenant_id: $tenant_id})
                    MATCH (t:Tool {name: $tool_name, tenant_id: $tenant_id})
                    CREATE (a)-[:HAS_TOOL]->(t)
                """, {
                    "agent_name": agent_name,
                    "tool_name": tool_name,
                    "tenant_id": tenant_id
                })
                tool_count += 1
        
        print(f"   ✅ Created {tool_count} agent-tool relationships")
        
        # Supervision relationships (workers)
        supervision_count = 0
        for agent_name, agent_config in AGENTS.items():
            parent = agent_config["parent"]
            self.execute("""
                MATCH (parent:Agent {name: $parent_name, tenant_id: $tenant_id})
                MATCH (child:Agent {name: $child_name, tenant_id: $tenant_id})
                CREATE (parent)-[:SUPERVISES {priority: 1, can_retry: true, max_retries: 2}]->(child)
            """, {
                "parent_name": parent,
                "child_name": agent_name,
                "tenant_id": tenant_id
            })
            supervision_count += 1
        
        # Supervision relationships (supervisors)
        for supervisor_name, supervisor_config in SUPERVISORS.items():
            if supervisor_config["parent"]:
                self.execute("""
                    MATCH (parent:Agent {name: $parent_name, tenant_id: $tenant_id})
                    MATCH (child:Agent {name: $child_name, tenant_id: $tenant_id})
                    CREATE (parent)-[:SUPERVISES {priority: 1}]->(child)
                """, {
                    "parent_name": supervisor_config["parent"],
                    "child_name": supervisor_name,
                    "tenant_id": tenant_id
                })
                supervision_count += 1
        
        print(f"   ✅ Created {supervision_count} supervision relationships")
        
        # Tenant relationships
        self.execute("""
            MATCH (t:Tenant {id: $tenant_id})
            MATCH (a:Agent {tenant_id: $tenant_id})
            CREATE (a)-[:BELONGS_TO]->(t)
        """, {"tenant_id": tenant_id})
        
        self.execute("""
            MATCH (t:Tenant {id: $tenant_id})
            MATCH (tool:Tool {tenant_id: $tenant_id})
            CREATE (tool)-[:BELONGS_TO]->(t)
        """, {"tenant_id": tenant_id})
        
        print("✅ All relationships created")
    
    def verify_migration(self, tenant_id: str):
        """Verify the migration was successful"""
        print("\n🔍 Verifying migration...")
        
        # Count agents
        result = self.execute("""
            MATCH (a:Agent {tenant_id: $tenant_id})
            RETURN count(a) as count
        """, {"tenant_id": tenant_id})
        agent_count = result[0]["count"]
        expected_agents = len(AGENTS) + len(SUPERVISORS)
        
        print(f"   Agents: {agent_count}/{expected_agents} {'✅' if agent_count == expected_agents else '❌'}")
        
        # Count tools
        result = self.execute("""
            MATCH (t:Tool {tenant_id: $tenant_id})
            RETURN count(t) as count
        """, {"tenant_id": tenant_id})
        tool_count = result[0]["count"]
        expected_tools = len(TOOLS)
        
        print(f"   Tools: {tool_count}/{expected_tools} {'✅' if tool_count == expected_tools else '❌'}")
        
        # Count relationships
        result = self.execute("""
            MATCH (a:Agent {tenant_id: $tenant_id})-[:SUPERVISES]->()
            RETURN count(*) as count
        """, {"tenant_id": tenant_id})
        supervision_count = result[0]["count"]
        
        print(f"   Supervision relationships: {supervision_count} ✅")
        
        result = self.execute("""
            MATCH (a:Agent {tenant_id: $tenant_id})-[:HAS_TOOL]->()
            RETURN count(*) as count
        """, {"tenant_id": tenant_id})
        tool_rel_count = result[0]["count"]
        
        print(f"   Tool relationships: {tool_rel_count} ✅")
        
        # Check root exists
        result = self.execute("""
            MATCH (a:Agent {name: 'root_supervisor', tenant_id: $tenant_id})
            RETURN a.name as name
        """, {"tenant_id": tenant_id})
        
        if result:
            print(f"   Root supervisor: {result[0]['name']} ✅")
        else:
            print("   Root supervisor: NOT FOUND ❌")
        
        print("\n✅ Migration verification complete!")
    
    def migrate(self, tenant_id: str, tenant_name: str = None, clear_existing: bool = False):
        """Run full migration"""
        print("=" * 70)
        print("🚀 NEO4J AGENT MIGRATION")
        print("=" * 70)
        print(f"Tenant: {tenant_id}")
        print(f"Clear existing: {clear_existing}")
        print()
        
        try:
            # Step 1: Create indexes
            self.create_indexes()
            
            # Step 2: Clear existing data if requested
            if clear_existing:
                self.clear_tenant_data(tenant_id)
            
            # Step 3: Create tenant
            self.create_tenant(tenant_id, tenant_name)
            
            # Step 4: Create tools
            self.create_tools(tenant_id)
            
            # Step 5: Create agents
            self.create_agents(tenant_id)
            
            # Step 6: Create relationships
            self.create_relationships(tenant_id)
            
            # Step 7: Verify
            self.verify_migration(tenant_id)
            
            print("\n" + "=" * 70)
            print("🎉 MIGRATION COMPLETE!")
            print("=" * 70)
            print("\nNext steps:")
            print("  1. Test with: python3 test_meta_swarm.py")
            print("  2. Verify in Neo4j Browser:")
            print("     MATCH (t:Tenant {id: '" + tenant_id + "'})<-[:BELONGS_TO]-(a:Agent)")
            print("     RETURN t, a")
            print()
            
        except Exception as e:
            print(f"\n❌ Migration failed: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Migrate agent config to Neo4j")
    parser.add_argument(
        "--tenant-id",
        default="default",
        help="Tenant ID (default: 'default')"
    )
    parser.add_argument(
        "--tenant-name",
        help="Tenant name (default: 'Tenant <tenant_id>')"
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear existing data before migration"
    )
    parser.add_argument(
        "--neo4j-uri",
        default=os.getenv("NEO4J_URI"),
        help="Neo4j URI (default: from NEO4J_URI env)"
    )
    parser.add_argument(
        "--neo4j-user",
        default=os.getenv("NEO4J_USER"),
        help="Neo4j user (default: from NEO4J_USER env)"
    )
    parser.add_argument(
        "--neo4j-password",
        default=os.getenv("NEO4J_PASSWORD"),
        help="Neo4j password (default: from NEO4J_PASSWORD env)"
    )
    
    args = parser.parse_args()
    
    # Validate Neo4j connection
    if not all([args.neo4j_uri, args.neo4j_user, args.neo4j_password]):
        print("❌ Error: Neo4j connection details required")
        print("   Set NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD environment variables")
        print("   Or pass --neo4j-uri, --neo4j-user, --neo4j-password flags")
        sys.exit(1)
    
    # Run migration
    migration = Neo4jMigration(
        uri=args.neo4j_uri,
        user=args.neo4j_user,
        password=args.neo4j_password
    )
    
    try:
        migration.migrate(
            tenant_id=args.tenant_id,
            tenant_name=args.tenant_name,
            clear_existing=args.clear
        )
    finally:
        migration.close()


if __name__ == "__main__":
    main()
