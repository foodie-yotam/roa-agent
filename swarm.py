"""
ROA Swarm - Simple, No Hardcoded Paths
Just one file that builds the agent graph. That's it.
"""

import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from langgraph.graph import StateGraph, MessagesState, START
from utils.node_factory import create_worker_node, create_team_caller

# Import tools from agent.py (where they currently live)
from agent import (
    search_recipes, get_recipe_details,
    get_team_members, assign_task,
    suggest_dishes,
    check_stock, list_suppliers, forecast_demand,
    calculate_cost,
    display_recipes, display_multiplication, display_prediction_graph, 
    display_inventory_alert, display_team_assignment,
    create_marketing_content,
    generate_tool_code,
    make_supervisor_node,
    State,
)

# ============================================================================
# CONFIGURATION - Just edit these strings!
# ============================================================================

# LLM
llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    google_api_key=os.getenv("GOOGLE_API_KEY", "AIzaSyAPxogxsFokL6Ty0mmlIn3YuP3-AtKSd5U"),
    temperature=0,
)

# Agent names (used for routing)
AGENTS = {
    "visualization": ["display_recipes", "display_multiplication", "display_prediction_graph", 
                     "display_inventory_alert", "display_team_assignment"],
    "marketing": ["create_marketing_content"],
    "dev_tools": ["generate_tool_code"],
    "recipe": ["search_recipes", "get_recipe_details"],
    "team_pm": ["get_team_members", "assign_task"],
    "dish_ideation": ["suggest_dishes"],
    "stock": ["check_stock"],
    "suppliers": ["list_suppliers"],
    "analysis": ["forecast_demand"],
    "profit": ["calculate_cost"],
}

# Prompts as strings (edit these directly!)
PROMPTS = {
    "visualization": """You are a visualization specialist for kitchen operations.
Create visual displays when users need to SEE data graphically.
ONLY create visualizations when explicitly requested or clearly beneficial.""",

    "marketing": """You are a marketing content creator for culinary products.
Generate marketing copy and promotional content.
ONLY handle marketing/promotional content requests.""",

    "dev_tools": """You are a developer tool assistant.
Generate Python code for tools and scripts.
ONLY handle code generation requests.""",

    "recipe": """You are a recipe database specialist with access to Neo4j database.
Search and retrieve recipe information from Neo4j.
ONLY handle recipe operations - NOT inventory, team, or sales.""",

    "team_pm": """You are a team project manager.
Manage team members, tasks, and assignments.
ONLY handle team management operations.""",

    "dish_ideation": """You are a dish ideation specialist.
Suggest dish ideas based on ingredients.
ONLY handle dish ideation requests.""",

    "stock": """You are an inventory management specialist.
Check stock levels and manage inventory.
ONLY handle inventory management operations.""",

    "suppliers": """You are a supplier management specialist.
Manage suppliers and their information.
ONLY handle supplier management operations.""",

    "analysis": """You are a demand forecasting specialist.
Forecast demand for items.
ONLY handle demand forecasting operations.""",

    "profit": """You are a profitability analyst.
Calculate costs and analyze profit margins.
ONLY handle cost/profit analysis operations.""",
}

# ============================================================================
# BUILD AGENTS - Simple function mapping
# ============================================================================

def get_tools(agent_name):
    """Get tools for an agent by name"""
    tool_names = AGENTS[agent_name]
    tool_map = {
        "search_recipes": search_recipes,
        "get_recipe_details": get_recipe_details,
        "get_team_members": get_team_members,
        "assign_task": assign_task,
        "suggest_dishes": suggest_dishes,
        "check_stock": check_stock,
        "list_suppliers": list_suppliers,
        "forecast_demand": forecast_demand,
        "calculate_cost": calculate_cost,
        "display_recipes": display_recipes,
        "display_multiplication": display_multiplication,
        "display_prediction_graph": display_prediction_graph,
        "display_inventory_alert": display_inventory_alert,
        "display_team_assignment": display_team_assignment,
        "create_marketing_content": create_marketing_content,
        "generate_tool_code": generate_tool_code,
    }
    return [tool_map[name] for name in tool_names]

def build_agent(name):
    """Build an agent with prompt and tools"""
    return create_react_agent(
        llm,
        get_tools(name),
        prompt=PROMPTS[name]
    )

# ============================================================================
# BUILD GRAPHS - Hierarchical teams
# ============================================================================

# Kitchen Team
kitchen_agents = {
    "recipe": build_agent("recipe"),
    "team_pm": build_agent("team_pm"),
    "dish_ideation": build_agent("dish_ideation"),
}

kitchen_supervisor = make_supervisor_node(
    llm,
    ["recipe", "team_pm", "dish_ideation"],
    worker_tools={
        "recipe": get_tools("recipe"),
        "team_pm": get_tools("team_pm"),
        "dish_ideation": get_tools("dish_ideation"),
    }
)

kitchen_builder = StateGraph(State)
kitchen_builder.add_node("supervisor", kitchen_supervisor)
kitchen_builder.add_node("recipe", create_worker_node("recipe", kitchen_agents["recipe"]))
kitchen_builder.add_node("team_pm", create_worker_node("team_pm", kitchen_agents["team_pm"]))
kitchen_builder.add_node("dish_ideation", create_worker_node("dish_ideation", kitchen_agents["dish_ideation"]))
kitchen_builder.add_edge(START, "supervisor")
kitchen_team_graph = kitchen_builder.compile()

# Inventory Team
inventory_agents = {
    "stock": build_agent("stock"),
    "suppliers": build_agent("suppliers"),
    "analysis": build_agent("analysis"),
}

inventory_supervisor = make_supervisor_node(
    llm,
    ["stock", "suppliers", "analysis"],
    worker_tools={
        "stock": get_tools("stock"),
        "suppliers": get_tools("suppliers"),
        "analysis": get_tools("analysis"),
    }
)

inventory_builder = StateGraph(State)
inventory_builder.add_node("supervisor", inventory_supervisor)
inventory_builder.add_node("stock", create_worker_node("stock", inventory_agents["stock"]))
inventory_builder.add_node("suppliers", create_worker_node("suppliers", inventory_agents["suppliers"]))
inventory_builder.add_node("analysis", create_worker_node("analysis", inventory_agents["analysis"]))
inventory_builder.add_edge(START, "supervisor")
inventory_team_graph = inventory_builder.compile()

# Sales Team
profit_agent = build_agent("profit")

sales_supervisor = make_supervisor_node(
    llm,
    ["profit"],
    worker_tools={"profit": get_tools("profit")}
)

sales_builder = StateGraph(State)
sales_builder.add_node("supervisor", sales_supervisor)
sales_builder.add_node("profit", create_worker_node("profit", profit_agent))
sales_builder.add_edge(START, "supervisor")
sales_team_graph = sales_builder.compile()

# Chef Team (combines kitchen, inventory, sales)
call_kitchen_team = create_team_caller("kitchen_team", kitchen_team_graph)
call_inventory_team = create_team_caller("inventory_team", inventory_team_graph)
call_sales_team = create_team_caller("sales_team", sales_team_graph)

chef_supervisor = make_supervisor_node(
    llm,
    ["kitchen_team", "inventory_team", "sales_team"],
    worker_tools={
        "kitchen_team": "Manages recipes, team assignments, and dish planning",
        "inventory_team": "Tracks stock, suppliers, and demand forecasting",
        "sales_team": "Analyzes costs and profitability"
    }
)

chef_builder = StateGraph(State)
chef_builder.add_node("supervisor", chef_supervisor)
chef_builder.add_node("kitchen_team", call_kitchen_team)
chef_builder.add_node("inventory_team", call_inventory_team)
chef_builder.add_node("sales_team", call_sales_team)
chef_builder.add_edge(START, "supervisor")
chef_team_graph = chef_builder.compile()

# Builder Team
dev_tools_agent = build_agent("dev_tools")

builder_supervisor = make_supervisor_node(
    llm,
    ["dev_tools"],
    worker_tools={"dev_tools": get_tools("dev_tools")}
)

builder_builder = StateGraph(State)
builder_builder.add_node("supervisor", builder_supervisor)
builder_builder.add_node("dev_tools", create_worker_node("dev_tools", dev_tools_agent))
builder_builder.add_edge(START, "supervisor")
builder_team_graph = builder_builder.compile()

# Root level agents
visualization_agent = build_agent("visualization")
marketing_agent = build_agent("marketing")

# Root Graph (combines everything)
call_chef_team = create_team_caller("chef_team", chef_team_graph)
call_builder_team = create_team_caller("builder_team", builder_team_graph)

root_supervisor = make_supervisor_node(
    llm,
    ["visualization", "marketing", "builder_team", "chef_team"],
    worker_tools={
        "visualization": get_tools("visualization"),
        "marketing": get_tools("marketing"),
        "builder_team": get_tools("dev_tools"),
        "chef_team": "Handles ALL kitchen operations: recipes, inventory, costs, team management"
    }
)

root_builder = StateGraph(State)
root_builder.add_node("supervisor", root_supervisor)
root_builder.add_node("visualization", create_worker_node("visualization", visualization_agent))
root_builder.add_node("marketing", create_worker_node("marketing", marketing_agent))
root_builder.add_node("builder_team", call_builder_team)
root_builder.add_node("chef_team", call_chef_team)
root_builder.add_edge(START, "supervisor")

# ============================================================================
# EXPORT - LangGraph Cloud will use this
# ============================================================================
agent = root_builder.compile()
