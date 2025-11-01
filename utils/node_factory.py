"""
Node Factory - Eliminates duplication in node wrappers

Instead of writing 13 identical node functions, use these factories.
"""

from typing import Literal
from langchain_core.messages import HumanMessage
from langgraph.types import Command


def create_worker_node(name: str, agent):
    """Factory: Creates a node wrapper for any worker agent
    
    Args:
        name: Agent name (e.g., "recipe", "team_pm")
        agent: LangGraph agent (from create_react_agent)
        
    Returns:
        Node function that invokes agent and returns to supervisor
        
    Example:
        recipe_node = create_worker_node("recipe", recipe_agent)
        # Instead of writing 12 lines manually!
    """
    def node(state) -> Command[Literal["supervisor"]]:
        result = agent.invoke(state)
        return Command(
            update={"messages": [HumanMessage(
                content=result["messages"][-1].content,
                name=name
            )]},
            goto="supervisor"
        )
    
    # Set function name for debugging
    node.__name__ = f"{name}_node"
    return node


def create_team_caller(name: str, team_graph):
    """Factory: Creates a caller for a compiled team subgraph
    
    Args:
        name: Team name (e.g., "kitchen_team", "chef_team")
        team_graph: Compiled LangGraph graph
        
    Returns:
        Node function that invokes team graph and returns to supervisor
        
    Example:
        call_kitchen_team = create_team_caller("kitchen_team", kitchen_graph)
    """
    def caller(state) -> Command[Literal["supervisor"]]:
        response = team_graph.invoke({"messages": state["messages"]})
        return Command(
            update={"messages": [HumanMessage(
                content=response["messages"][-1].content,
                name=name
            )]},
            goto="supervisor"
        )
    
    # Set function name for debugging
    caller.__name__ = f"call_{name}"
    return caller
