"""Supervisor helper for routing between workers"""
from typing import Literal
from typing_extensions import TypedDict
from langgraph.graph import END
from langgraph.types import Command
from .state import State


def make_supervisor_node(llm, members: list[str]):
    """Create a supervisor node that routes to team members
    
    Args:
        llm: Language model to use for routing decisions
        members: List of worker names that supervisor can route to
        
    Returns:
        Supervisor node function that returns Command with routing decision
    """
    options = ["FINISH"] + members
    system_prompt = (
        f"You are a supervisor managing these workers: {members}. "
        "CRITICAL RULES:\n"
        "1. DEFAULT TO FINISH - Only delegate if the user's request SPECIFICALLY needs one of your workers\n"
        "2. If a worker just responded with an answer, respond with FINISH immediately\n"
        "3. Each worker should be called ONCE maximum per request\n"
        "4. If the request doesn't match any of your workers' expertise, respond with FINISH\n"
        "5. If you're unsure, choose FINISH rather than delegating\n\n"
        f"Your available workers: {members}\n"
        "Respond with the worker name ONLY if their expertise is required, otherwise respond with FINISH."
    )
    
    class Router(TypedDict):
        """Worker to route to next"""
        next: Literal[tuple(options)]
    
    def supervisor_node(state: State) -> Command[Literal[tuple(members + ["__end__"])]]:
        messages = [{"role": "system", "content": system_prompt}] + state["messages"]
        response = llm.with_structured_output(Router).invoke(messages)
        goto = response["next"]
        if goto == "FINISH":
            goto = END
        return Command(goto=goto, update={"next": goto})
    
    return supervisor_node
