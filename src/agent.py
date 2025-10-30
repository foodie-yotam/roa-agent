"""
ROA Agent - Hierarchical Multi-Agent System
Refactored with proper structure: teams as folders, agents as files
"""
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, START
from langgraph.types import Command
from typing import Literal

from .shared.state import State
from .shared.supervisor import make_supervisor_node
from .teams.speaker.team import create_speaker_team
from .teams.chef.kitchen.agents.recipe import create_recipe_agent

# Initialize LLM
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",  # Higher rate limit (2K RPM vs 10 RPM)
    temperature=0.7,
    google_api_key=GOOGLE_API_KEY
)

print(f"🤖 Using model: gemini-2.0-flash")


# ========================================================================
# ROOT GRAPH - Top level orchestration
# ========================================================================

def create_root_agent():
    """Create the root agent with all teams"""
    
    # Create team graphs
    speaker_team = create_speaker_team(llm)
    
    # Team delegation nodes
    def call_speaker_team(state: State) -> Command[Literal["supervisor"]]:
        response = speaker_team.invoke({"messages": state["messages"]})
        return Command(
            update={"messages": [HumanMessage(content=response["messages"][-1].content, name="speaker_team")]},
            goto="supervisor"
        )
    
    # Chef team with recipe agent
    recipe_agent = create_recipe_agent(llm)
    
    def call_chef_team(state: State) -> Command[Literal["supervisor"]]:
        # Call recipe agent directly for now (simplified chef team)
        result = recipe_agent.invoke({"messages": state["messages"]})
        return Command(
            update={"messages": [HumanMessage(content=result["messages"][-1].content, name="chef_team")]},
            goto="supervisor"
        )
    
    def call_builder_team(state: State) -> Command[Literal["supervisor"]]:
        return Command(
            update={"messages": [HumanMessage(content="Builder team: Not yet implemented in refactor", name="builder_team")]},
            goto="supervisor"
        )
    
    # Create root supervisor (speaker_team disabled for now)
    root_supervisor = make_supervisor_node(llm, ["chef_team"])
    
    # Build root graph (only chef_team enabled for now)
    builder = StateGraph(State)
    builder.add_node("supervisor", root_supervisor)
    builder.add_node("chef_team", call_chef_team)
    
    builder.add_edge(START, "supervisor")
    
    return builder.compile()


# Export as 'agent' for LangGraph Cloud
agent = create_root_agent()


# ========================================================================
# TESTING
# ========================================================================

if __name__ == "__main__":
    print("\n" + "="*80)
    print("Testing ROA Agent - Refactored Structure")
    print("="*80 + "\n")
    
    config = {"configurable": {"thread_id": "test-1"}}
    
    # Test voice
    print("Test 1: Voice response")
    result = agent.invoke(
        {"messages": [{"role": "user", "content": "Generate a voice response welcoming customers"}]},
        config
    )
    print(f"Response: {result['messages'][-1].content}\n")
    
    # Test video
    print("Test 2: Video visualization")
    result = agent.invoke(
        {"messages": [{"role": "user", "content": "Show me pasta recipes"}]},
        config
    )
    print(f"Response: {result['messages'][-1].content}\n")
