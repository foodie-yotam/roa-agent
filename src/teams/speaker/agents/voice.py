"""Text response agent - handles direct user conversation (server handles voice/TTS)"""
from langchain_core.messages import AIMessage
from langgraph.graph import StateGraph, START, END

from ....shared.state import State


def create_voice_agent(llm):
    """Create text response agent (simplified - no voice tools needed)
    
    Server handles voice conversion via OpenAI Whisper (STT) and ElevenLabs (TTS).
    This agent just responds naturally with text.
    
    Returns:
        Compiled text response agent graph
    """
    def agent_node(state: State):
        messages = state["messages"]
        system_msg = AIMessage(
            role="system",
            content="You are a helpful restaurant operations assistant. "
                    "Respond naturally and concisely. The user may be using voice, "
                    "so keep responses conversational but professional."
        )
        response = llm.invoke([system_msg] + messages)
        return {"messages": [response]}
    
    # Simple single-node graph
    builder = StateGraph(State)
    builder.add_node("agent", agent_node)
    builder.add_edge(START, "agent")
    builder.add_edge("agent", END)
    
    return builder.compile()
