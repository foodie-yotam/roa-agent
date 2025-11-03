"""
Meta-Swarm: Dynamic Agent Graph Builder from Neo4j

Loads agent hierarchy, prompts, and tools from Neo4j database
and builds a LangGraph swarm at runtime.

Usage:
    agent = load_swarm_from_neo4j(tenant_id="restaurant_abc")
"""

import os
import importlib
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from neo4j import GraphDatabase

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from langgraph.graph import StateGraph, START
from langgraph.types import Command

# Import factory functions and State
from utils.node_factory import create_worker_node, create_team_caller
from agent import State, make_supervisor_node


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class AgentData:
    """Agent loaded from Neo4j"""
    id: str
    name: str
    type: str  # "worker" or "supervisor"
    prompt: str
    enabled: bool
    metadata: Dict
    tools: List[str]
    parent: Optional[str]  # Parent supervisor name


@dataclass
class ToolData:
    """Tool loaded from Neo4j"""
    name: str
    module: str
    function: str


# ============================================================================
# NEO4J CONNECTION
# ============================================================================

class Neo4jConnection:
    """Manages Neo4j database connection"""
    
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
    
    def close(self):
        self.driver.close()
    
    def query(self, cypher: str, parameters: Dict = None):
        """Execute Cypher query and return results"""
        with self.driver.session() as session:
            result = session.run(cypher, parameters or {})
            return [record for record in result]


# ============================================================================
# SWARM LOADER
# ============================================================================

class MetaSwarmLoader:
    """Loads and builds agent swarm from Neo4j"""
    
    def __init__(self, tenant_id: str, neo4j_uri: str = None, neo4j_user: str = None, neo4j_password: str = None):
        self.tenant_id = tenant_id
        
        # Neo4j connection
        self.db = Neo4jConnection(
            uri=neo4j_uri or os.getenv("NEO4J_URI"),
            user=neo4j_user or os.getenv("NEO4J_USER"),
            password=neo4j_password or os.getenv("NEO4J_PASSWORD")
        )
        
        # LLM
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-exp",
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            temperature=0,
        )
        
        # Caches
        self.agents_cache: Dict[str, Any] = {}
        self.tools_cache: Dict[str, Any] = {}
        self.graphs_cache: Dict[str, Any] = {}
    
    def load_agents(self) -> List[AgentData]:
        """Load all enabled agents for tenant from Neo4j"""
        
        query = """
        MATCH (a:Agent {tenant_id: $tenant_id, enabled: true})
        OPTIONAL MATCH (a)-[:HAS_TOOL]->(t:Tool)
        OPTIONAL MATCH (parent)-[:SUPERVISES]->(a)
        RETURN 
            a.id as id,
            a.name as name,
            a.type as type,
            a.prompt as prompt,
            a.enabled as enabled,
            a.metadata as metadata,
            collect(DISTINCT t.name) as tools,
            parent.name as parent
        ORDER BY 
            CASE a.type 
                WHEN 'supervisor' THEN 0 
                ELSE 1 
            END,
            a.name
        """
        
        results = self.db.query(query, {"tenant_id": self.tenant_id})
        
        agents = []
        for record in results:
            agents.append(AgentData(
                id=record["id"],
                name=record["name"],
                type=record["type"],
                prompt=record["prompt"] or "You are a helpful assistant.",
                enabled=record["enabled"],
                metadata=record["metadata"] or {},
                tools=[t for t in record["tools"] if t],  # Filter nulls
                parent=record["parent"]
            ))
        
        return agents
    
    def load_tool(self, tool_name: str) -> Any:
        """Load tool function from module"""
        
        if tool_name in self.tools_cache:
            return self.tools_cache[tool_name]
        
        # Query tool definition
        query = """
        MATCH (t:Tool {name: $tool_name})
        RETURN t.module as module, t.function as function
        LIMIT 1
        """
        
        results = self.db.query(query, {"tool_name": tool_name})
        
        if not results:
            raise ValueError(f"Tool '{tool_name}' not found in Neo4j")
        
        module_path = results[0]["module"]
        function_name = results[0]["function"]
        
        # Dynamically import
        module = importlib.import_module(module_path)
        tool_func = getattr(module, function_name)
        
        self.tools_cache[tool_name] = tool_func
        return tool_func
    
    def build_worker_agent(self, agent_data: AgentData):
        """Build a worker agent from Neo4j data"""
        
        # Load tools
        tools = [self.load_tool(tool_name) for tool_name in agent_data.tools]
        
        # Create agent with prompt from DB
        agent = create_react_agent(
            self.llm,
            tools,
            prompt=agent_data.prompt  # ← From Neo4j!
        )
        
        return agent, tools
    
    def build_supervisor_agent(self, agent_data: AgentData, worker_names: List[str], worker_tools: Dict[str, List] = None):
        """Build a supervisor agent"""
        
        # Use existing supervisor builder
        supervisor_node = make_supervisor_node(
            self.llm,
            worker_names,
            worker_tools=worker_tools
        )
        
        return supervisor_node
    
    def build_team_graph(self, supervisor_name: str, agents: List[AgentData]) -> Any:
        """Build a sub-graph for a team (supervisor + workers)"""
        
        # Find supervisor
        supervisor = next((a for a in agents if a.name == supervisor_name), None)
        if not supervisor or supervisor.type != "supervisor":
            raise ValueError(f"Supervisor '{supervisor_name}' not found or not a supervisor")
        
        # Find workers supervised by this supervisor
        workers = [a for a in agents if a.parent == supervisor_name]
        worker_names = [w.name for w in workers]
        
        if not workers:
            raise ValueError(f"Supervisor '{supervisor_name}' has no workers")
        
        # Build worker agents
        worker_agents = {}
        worker_tools = {}
        for worker in workers:
            if worker.type == "worker":
                agent, tools = self.build_worker_agent(worker)
                worker_agents[worker.name] = agent
                worker_tools[worker.name] = tools
            elif worker.type == "supervisor":
                # Recursive: worker is actually a sub-supervisor
                sub_graph = self.build_team_graph(worker.name, agents)
                worker_agents[worker.name] = sub_graph
                worker_tools[worker.name] = f"Sub-team: {worker.metadata.get('description', worker.name)}"
        
        # Build supervisor
        supervisor_node = self.build_supervisor_agent(supervisor, worker_names, worker_tools)
        
        # Build graph
        builder = StateGraph(State)
        builder.add_node("supervisor", supervisor_node)
        
        for worker_name, worker_agent in worker_agents.items():
            if isinstance(worker_agent, StateGraph) or hasattr(worker_agent, "nodes"):
                # Sub-graph (team)
                node_func = create_team_caller(worker_name, worker_agent)
            else:
                # Regular worker
                node_func = create_worker_node(worker_name, worker_agent)
            
            builder.add_node(worker_name, node_func)
        
        builder.add_edge(START, "supervisor")
        
        compiled = builder.compile()
        self.graphs_cache[supervisor_name] = compiled
        return compiled
    
    def build_swarm(self) -> Any:
        """Build the complete agent swarm from Neo4j"""
        
        print(f"🚀 Loading swarm from Neo4j for tenant: {self.tenant_id}")
        
        # Load all agents
        agents = self.load_agents()
        
        if not agents:
            raise ValueError(f"No agents found for tenant '{self.tenant_id}'")
        
        print(f"   Found {len(agents)} agents")
        
        # Find root supervisor
        root = next((a for a in agents if a.parent is None and a.type == "supervisor"), None)
        
        if not root:
            raise ValueError(f"No root supervisor found for tenant '{self.tenant_id}'")
        
        print(f"   Root supervisor: {root.name}")
        
        # Build from root
        root_graph = self.build_team_graph(root.name, agents)
        
        print(f"✅ Swarm built successfully!")
        print(f"   Nodes: {list(root_graph.nodes.keys())}")
        
        return root_graph
    
    def close(self):
        """Close Neo4j connection"""
        self.db.close()


# ============================================================================
# PUBLIC API
# ============================================================================

def load_swarm_from_neo4j(tenant_id: str = "default") -> Any:
    """
    Load agent swarm from Neo4j for specific tenant.
    
    Args:
        tenant_id: Restaurant/customer ID (default: "default")
    
    Returns:
        Compiled LangGraph agent swarm
    
    Example:
        agent = load_swarm_from_neo4j(tenant_id="restaurant_abc")
        result = agent.invoke({"messages": [{"role": "user", "content": "Find arroz sushi recipe"}]})
    """
    loader = MetaSwarmLoader(tenant_id)
    
    try:
        swarm = loader.build_swarm()
        return swarm
    finally:
        loader.close()


# ============================================================================
# TENANT SWARM CACHE (for production)
# ============================================================================

_TENANT_SWARMS: Dict[str, Any] = {}

def get_swarm(tenant_id: str, force_reload: bool = False) -> Any:
    """
    Get cached swarm for tenant, or load from Neo4j if not cached.
    
    Args:
        tenant_id: Restaurant/customer ID
        force_reload: Force reload from Neo4j (invalidate cache)
    
    Returns:
        Compiled LangGraph agent swarm
    """
    global _TENANT_SWARMS
    
    if force_reload or tenant_id not in _TENANT_SWARMS:
        print(f"🔄 Loading swarm for tenant: {tenant_id}")
        _TENANT_SWARMS[tenant_id] = load_swarm_from_neo4j(tenant_id)
    
    return _TENANT_SWARMS[tenant_id]


def invalidate_tenant_cache(tenant_id: str):
    """Invalidate cached swarm for tenant (call after agent updates)"""
    if tenant_id in _TENANT_SWARMS:
        del _TENANT_SWARMS[tenant_id]
        print(f"🗑️  Invalidated cache for tenant: {tenant_id}")


# ============================================================================
# EXPORT FOR LANGGRAPH CLOUD
# ============================================================================

# Default tenant for single-restaurant deployment
agent = load_swarm_from_neo4j(tenant_id=os.getenv("TENANT_ID", "default"))
