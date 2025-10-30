"""Marketing agent - creates marketing content"""
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode

from ....shared.state import State
from ..tools import create_marketing_content


def create_marketing_agent(llm):
    """Create marketing agent with individual tool nodes
    
    Returns:
        Compiled marketing agent graph
    """
    tools = [create_marketing_content]
    llm_with_tools = llm.bind_tools(tools)
    
    def agent_node(state: State):
        messages = state["messages"]
        system_msg = {
            "role": "system",
            "content": "You are the Marketing Specialist. Create compelling marketing content."
        }
        response = llm_with_tools.invoke([system_msg] + messages)
        return {"messages": [response]}
    
    def route_tools(state: State):
        ai_message = state["messages"][-1]
        if not hasattr(ai_message, "tool_calls") or not ai_message.tool_calls:
            return END
        return ai_message.tool_calls[0]["name"]
    
    builder = StateGraph(State)
    builder.add_node("agent", agent_node)
    builder.add_node("create_marketing_content", ToolNode([create_marketing_content]))
    
    builder.add_edge(START, "agent")
    builder.add_conditional_edges(
        "agent",
        route_tools,
        ["create_marketing_content", END]
    )
    builder.add_edge("create_marketing_content", "agent")
    
    return builder.compile()
