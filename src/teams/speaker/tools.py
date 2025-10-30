"""Tools for speaker team"""
from typing import List
from langchain_core.tools import tool
import json


# --- Voice Tools ---
@tool
def generate_voice_response(text: str, tone: str = "professional") -> str:
    """Generate a natural text response (voice conversion handled by server)
    
    Args:
        text: The response text
        tone: Tone of voice (professional, casual, friendly) - for context only
    """
    return text


@tool
def text_to_speech(text: str) -> str:
    """Return text for speech (TTS handled by server)
    
    Args:
        text: Text to return
    """
    return text


# --- Video Tools ---
@tool
def display_recipes(recipes: List[str]) -> str:
    """Display recipe cards in visual format with React Flow.
    
    Args:
        recipes: List of recipe names to display
    
    Returns:
        Text response with embedded visualization JSON
    """
    viz_json = json.dumps({
        "tool": "display_recipes",
        "params": {"recipes": recipes}
    })
    return f"Here are {len(recipes)} recipes: {', '.join(recipes)}. VISUALIZATION: {viz_json}"


@tool
def display_multiplication(a: int, b: int) -> str:
    """Show multiplication visualization
    
    Args:
        a: First number
        b: Second number
        
    Returns:
        Text response with embedded visualization JSON
    """
    result = a * b
    viz_json = json.dumps({
        "tool": "display_multiplication",
        "params": {"a": a, "b": b, "result": result}
    })
    return f"{a} × {b} = {result}. VISUALIZATION: {viz_json}"


@tool
def display_prediction_graph(predictions: List[float]) -> str:
    """Show prediction trend graph
    
    Args:
        predictions: List of predicted values
        
    Returns:
        Text response with embedded visualization JSON
    """
    viz_json = json.dumps({
        "tool": "display_prediction_graph",
        "params": {"predictions": predictions}
    })
    return f"Prediction trend showing {len(predictions)} data points. VISUALIZATION: {viz_json}"


@tool
def display_inventory_alert(item: str, current: int, minimum: int) -> str:
    """Show inventory alert visualization
    
    Args:
        item: Item name
        current: Current stock level
        minimum: Minimum required level
        
    Returns:
        Text response with embedded visualization JSON
    """
    viz_json = json.dumps({
        "tool": "display_inventory_alert",
        "params": {"item": item, "current": current, "minimum": minimum}
    })
    return f"Alert: {item} stock is at {current} (minimum: {minimum}). VISUALIZATION: {viz_json}"


@tool
def display_team_assignment(task: str, assignee: str) -> str:
    """Show team task assignment
    
    Args:
        task: Task description
        assignee: Person assigned to the task
    
    Returns:
        Text response with embedded visualization JSON
    """
    viz_json = json.dumps({
        "tool": "display_team_assignment",
        "params": {"task": task, "assignee": assignee}
    })
    return f"I've assigned '{task}' to {assignee}. VISUALIZATION: {viz_json}"


# --- Marketing Tools ---
@tool
def create_marketing_content(product: str) -> str:
    """Generate marketing copy
    
    Args:
        product: Product name
    """
    return f"MARKETING: Premium {product} - crafted with care"
