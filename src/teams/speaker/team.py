"""Speaker team - combines voice, video, and marketing agents"""
from typing import Literal
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, START
from langgraph.types import Command

from ...shared.state import State
from ...shared.supervisor import make_supervisor_node
from .agents.voice import create_voice_agent
from .agents.video import create_video_agent
from .agents.marketing import create_marketing_agent


def create_speaker_team(llm):
    """Create speaker team with supervisor and worker agents
    
    Returns:
        Compiled speaker team graph
    """
    # Create worker agents
    voice_agent = create_voice_agent(llm)
    video_agent = create_video_agent(llm)
    marketing_agent = create_marketing_agent(llm)
    
    # Worker nodes that delegate to subgraphs
    def voice_node(state: State) -> Command[Literal["supervisor"]]:
        result = voice_agent.invoke({"messages": state["messages"]})
        return Command(
            update={"messages": [HumanMessage(content=result["messages"][-1].content, name="voice")]},
            goto="supervisor"
        )
    
    def video_node(state: State) -> Command[Literal["supervisor"]]:
        result = video_agent.invoke({"messages": state["messages"]})
        return Command(
            update={"messages": [HumanMessage(content=result["messages"][-1].content, name="video")]},
            goto="supervisor"
        )
    
    def marketing_node(state: State) -> Command[Literal["supervisor"]]:
        result = marketing_agent.invoke({"messages": state["messages"]})
        return Command(
            update={"messages": [HumanMessage(content=result["messages"][-1].content, name="marketing")]},
            goto="supervisor"
        )
    
    # Create supervisor
    supervisor = make_supervisor_node(llm, ["voice", "video", "marketing"])
    
    # Build team graph
    builder = StateGraph(State)
    builder.add_node("supervisor", supervisor)
    builder.add_node("voice", voice_node)
    builder.add_node("video", video_node)
    builder.add_node("marketing", marketing_node)
    
    builder.add_edge(START, "supervisor")
    
    return builder.compile()
