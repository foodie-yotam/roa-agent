"""
Tool Registry - Single Source of Truth for All Tools

Instead of declaring tools in 7 different places, declare once here.
All agents and supervisors pull from this registry.

Usage:
    from tools.registry import TOOL_REGISTRY
    
    # Create agent
    recipe_agent = create_react_agent(llm, TOOL_REGISTRY["recipe"], ...)
    
    # Pass to supervisor
    supervisor = make_supervisor_node(llm, [...], worker_tools=TOOL_REGISTRY)
"""

# Tools will be imported from agent.py for now
# In the future, move tool definitions here for better organization

def get_tool_registry():
    """
    Returns tool registry mapping agent names to their tool lists.
    
    Import here to avoid circular dependencies.
    """
    from agent import (
        # Recipe tools
        search_recipes,
        get_recipe_details,
        # Team tools  
        get_team_members,
        assign_task,
        # Dish tools
        suggest_dishes,
        # Stock tools
        check_stock,
        # Supplier tools
        list_suppliers,
        # Analysis tools
        forecast_demand,
        # Profit tools
        calculate_cost,
        # Visualization tools
        display_recipes,
        display_multiplication,
        display_prediction_graph,
        display_inventory_alert,
        display_team_assignment,
        # Marketing tools
        create_marketing_content,
        # Builder tools
        generate_tool_code,
    )
    
    return {
        # Kitchen team agents
        "recipe": [search_recipes, get_recipe_details],
        "team_pm": [get_team_members, assign_task],
        "dish_ideation": [suggest_dishes],
        
        # Inventory team agents
        "stock": [check_stock],
        "suppliers": [list_suppliers],
        "analysis": [forecast_demand],
        
        # Sales team agents
        "profit": [calculate_cost],
        
        # Direct root agents
        "visualization": [
            display_recipes,
            display_multiplication,
            display_prediction_graph,
            display_inventory_alert,
            display_team_assignment
        ],
        "marketing": [create_marketing_content],
        "dev_tools": [generate_tool_code],
    }


# Lazy-loaded registry (imported when first accessed)
_registry = None

def get_tools_for_agent(agent_name: str) -> list:
    """Get tools for a specific agent"""
    global _registry
    if _registry is None:
        _registry = get_tool_registry()
    return _registry.get(agent_name, [])


def get_tools_for_team(team_agents: list) -> dict:
    """
    Get tools for multiple agents (for supervisor visibility)
    
    Args:
        team_agents: List of agent names, e.g., ["recipe", "team_pm", "dish_ideation"]
        
    Returns:
        Dict mapping agent names to tool lists
        
    Example:
        tools = get_tools_for_team(["recipe", "team_pm"])
        # {"recipe": [search_recipes, get_recipe_details], "team_pm": [...]}
    """
    global _registry
    if _registry is None:
        _registry = get_tool_registry()
    
    return {
        name: _registry[name]
        for name in team_agents
        if name in _registry
    }


# For backward compatibility and convenience
TOOL_REGISTRY = property(lambda self: get_tool_registry())
