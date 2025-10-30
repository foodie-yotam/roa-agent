"""Recipe agent - searches and manages recipes"""
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode

from .....shared.state import State
from ..tools import search_recipes, get_recipe_details


def create_recipe_agent(llm):
    """Create recipe agent with individual tool nodes"""
    tools = [search_recipes, get_recipe_details]
    llm_with_tools = llm.bind_tools(tools)
    
    def agent_node(state: State):
        response = llm_with_tools.invoke(state["messages"])
        return {"messages": [response]}
    
    def route_tools(state: State):
        ai_message = state["messages"][-1]
        if not hasattr(ai_message, "tool_calls") or not ai_message.tool_calls:
            return END
        return ai_message.tool_calls[0]["name"]
    
    builder = StateGraph(State)
    builder.add_node("agent", agent_node)
    builder.add_node("search_recipes", ToolNode([search_recipes]))
    builder.add_node("get_recipe_details", ToolNode([get_recipe_details]))
    
    builder.add_edge(START, "agent")
    builder.add_conditional_edges(
        "agent",
        route_tools,
        ["search_recipes", "get_recipe_details", END]
    )
    builder.add_edge("search_recipes", "agent")
    builder.add_edge("get_recipe_details", "agent")
    
    return builder.compile()
