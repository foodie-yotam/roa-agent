"""
Swarm Loader - Infrastructure as Code for LangGraph Agent Swarms

Loads agent configurations from YAML files and builds LangGraph graphs dynamically.
Enables "Swarm-as-Code" - decouple configuration from implementation.
"""

import yaml
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from importlib import import_module
from functools import partial

from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.types import Command
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
import os

# Import factory functions
from utils.node_factory import create_worker_node, create_team_caller


# State definition (same as in agent.py)
class State(MessagesState):
    """State shared across all hierarchical levels"""
    next: str
    routing_recommendations: str
    delegation_path: list
    attempts_at_level: dict
    delegation_depth: int


class SwarmLoader:
    """Load and build swarm from YAML configuration"""
    
    def __init__(self, config_path: str = "swarm_config/swarm.yaml"):
        self.config_path = Path(config_path)
        self.base_dir = self.config_path.parent
        
        with open(self.config_path) as f:
            self.config = yaml.safe_load(f)
        
        self.llm = self._init_llm()
        self.tool_registry = {}
        self.agent_cache = {}
        
    def _init_llm(self):
        """Initialize LLM from config"""
        llm_config = self.config['global_config']['llm']
        
        if llm_config['provider'] == 'google':
            return ChatGoogleGenerativeAI(
                model=llm_config['model'],
                temperature=llm_config.get('temperature', 0.7)
            )
        # Add other providers as needed
        
    def load_prompt(self, prompt_file: str) -> str:
        """Load prompt from markdown file"""
        # prompt_file already includes 'prompts/' prefix, base_dir is 'swarm_config'
        prompt_path = self.base_dir / prompt_file
        
        if not prompt_path.exists():
            print(f"⚠️  Prompt file not found: {prompt_path}, using default")
            return "You are a helpful assistant."
            
        with open(prompt_path) as f:
            return f.read()
    
    def load_agent_config(self, config_file: str) -> Dict[str, Any]:
        """Load agent configuration from YAML"""
        config_path = self.base_dir / config_file
        
        with open(config_path) as f:
            return yaml.safe_load(f)
    
    def load_tool(self, tool_name: str):
        """Dynamically load tool function from registry"""
        if tool_name in self.tool_registry:
            return self.tool_registry[tool_name]
            
        tool_config = self.config['tools'].get(tool_name)
        if not tool_config:
            raise ValueError(f"Tool {tool_name} not found in tool registry")
        
        # Import the module and get the function
        module = import_module(tool_config['module'])
        tool_func = getattr(module, tool_config['function'])
        
        self.tool_registry[tool_name] = tool_func
        return tool_func
    
    def build_worker_agent(self, agent_config: Dict[str, Any]):
        """Build a worker agent from config"""
        # Load system prompt from markdown file
        prompt_text = self.load_prompt(agent_config['system_prompt_file'])
        
        # Load tools
        tools = [self.load_tool(tool_name) for tool_name in agent_config['tools']]
        
        # Create agent with prompt from file!
        # LangGraph's create_react_agent accepts prompt= parameter
        agent = create_react_agent(
            self.llm, 
            tools, 
            prompt=prompt_text  # ← Prompt loaded from .md file!
        )
        
        return agent, tools
    
    def build_supervisor(self, supervisor_config: Dict[str, Any]) -> tuple:
        """Build a supervisor from config"""
        # Load workers
        workers = supervisor_config['workers']
        worker_names = [w['name'] for w in workers]
        
        # Build worker tools dict for visibility
        worker_tools = {}
        for worker in workers:
            agent_config = self.load_agent_config(worker['agent_config'])
            tools = [self.load_tool(t) for t in agent_config.get('tools', [])]
            worker_tools[worker['name']] = tools
        
        # Load supervisor prompt
        prompt_template = self.load_prompt(supervisor_config['system_prompt_file'])
        
        # Get routing config
        routing_config = supervisor_config.get('routing_config', {})
        
        # Build supervisor node with tool visibility
        # Import here to avoid circular dependency
        from agent import make_supervisor_node
        
        supervisor_node = make_supervisor_node(
            self.llm,
            worker_names,
            worker_tools=worker_tools if routing_config.get('show_tool_table') else None
        )
        
        return supervisor_node, worker_names, worker_tools
    
    def build_team_graph(self, team_name: str, team_config: Dict[str, Any]) -> StateGraph:
        """Build a team's StateGraph from hierarchical config"""
        
        if team_config['type'] == 'worker':
            # Worker agent - build agent and return
            agent_config = self.load_agent_config(team_config['config'])
            agent, tools = self.build_worker_agent(agent_config)
            return agent  # Return agent directly for workers
            
        elif team_config['type'] == 'supervisor':
            # Supervisor with children - build full subgraph
            supervisor_config = self.load_agent_config(team_config['config'])
            supervisor_node, worker_names, worker_tools = self.build_supervisor(supervisor_config)
            
            # Build the graph
            builder = StateGraph(State)
            builder.add_node("supervisor", supervisor_node)
            
            # Add child nodes
            for child_name, child_config in team_config.get('children', {}).items():
                # Recursively build child
                child_agent = self.build_team_graph(child_name, child_config)
                
                # Create node wrapper
                # Use factory function for node creation
                node_func = create_worker_node(child_name, child_agent)
                builder.add_node(child_name, node_func)
            
            builder.add_edge(START, "supervisor")
            return builder.compile()
    
    def build_swarm(self) -> StateGraph:
        """Build complete swarm from configuration"""
        print("🚀 Building swarm from configuration...")
        print(f"   Config: {self.config_path}")
        print(f"   Swarm: {self.config['name']} v{self.config['version']}")
        
        # Build from root
        root_config = self.config['hierarchy']['root']
        root_graph = self.build_team_graph('root', root_config)
        
        print("✅ Swarm built successfully!")
        return root_graph


def load_swarm(config_path: str = "swarm_config/swarm.yaml"):
    """Convenience function to load swarm from config"""
    loader = SwarmLoader(config_path)
    return loader.build_swarm()


# Example usage
if __name__ == "__main__":
    swarm = load_swarm()
    print("Swarm loaded and ready!")
