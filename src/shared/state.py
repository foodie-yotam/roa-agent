"""Shared state definitions for all agents"""
from langgraph.graph import MessagesState

class State(MessagesState):
    """State shared across all hierarchical levels"""
    next: str
