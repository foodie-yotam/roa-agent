"""Video agent - handles visual displays with React Flow"""
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langgraph.types import Command

from ....shared.state import State
from ..tools import (
    display_recipes,
    display_multiplication,
    display_prediction_graph,
    display_inventory_alert,
    display_team_assignment
)


def create_video_agent(llm):
    """Create video agent with individual tool nodes
    
    Returns:
        Compiled video agent graph
    """
    tools = [
        display_recipes,
        display_multiplication,
        display_prediction_graph,
        display_inventory_alert,
        display_team_assignment
    ]
    llm_with_tools = llm.bind_tools(tools)
    
    def agent_node(state: State):
        messages = state["messages"]
        system_msg = {
            "role": "system",
            "content": "You are the Video Visualization Specialist. Create visual displays using React Flow. Return visualization commands as JSON."
        }
        response = llm_with_tools.invoke([system_msg] + messages)
        return {"messages": [response]}
    
    def route_tools(state: State):
        ai_message = state["messages"][-1]
        if not hasattr(ai_message, "tool_calls") or not ai_message.tool_calls:
            return END
        return ai_message.tool_calls[0]["name"]
    
    # Build graph with individual tool nodes
    builder = StateGraph(State)
    builder.add_node("agent", agent_node)
    builder.add_node("display_recipes", ToolNode([display_recipes]))
    builder.add_node("display_multiplication", ToolNode([display_multiplication]))
    builder.add_node("display_prediction_graph", ToolNode([display_prediction_graph]))
    builder.add_node("display_inventory_alert", ToolNode([display_inventory_alert]))
    builder.add_node("display_team_assignment", ToolNode([display_team_assignment]))
    
    builder.add_edge(START, "agent")
    builder.add_conditional_edges(
        "agent",
        route_tools,
        [
            "display_recipes",
            "display_multiplication",
            "display_prediction_graph",
            "display_inventory_alert",
            "display_team_assignment",
            END
        ]
    )
    # All tools route back to agent
    for tool in tools:
        builder.add_edge(tool.name, "agent")
    
    return builder.compile()
