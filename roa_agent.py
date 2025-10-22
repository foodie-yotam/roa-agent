"""
ROA Database Agent - Main module for LangGraph server
"""

import os
from typing import TypedDict
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import tools_condition, ToolNode
from supabase import create_client, Client

# Database connection
SUPABASE_URL = os.getenv("SUPABASE_URL", "http://127.0.0.1:54321")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "sb_publishable_ACJWlzQHlZjBrEguHvfOxg_3BJgxAaH")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# LLM setup with Gemini
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "AIzaSyAPxogxsFokL6Ty0mmlIn3YuP3-AtKSd5U")
llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    google_api_key=GOOGLE_API_KEY,
    temperature=0
)

# Database query tools
def get_all_users() -> str:
    """Get all users in the system."""
    try:
        result = supabase.table("users").select("*").execute()
        return f"Users: {result.data}"
    except Exception as e:
        return f"Error: {str(e)}"

def get_all_kitchens() -> str:
    """Get all kitchens in the system."""
    try:
        result = supabase.table("kitchen").select("*").execute()
        return f"Kitchens: {result.data}"
    except Exception as e:
        return f"Error: {str(e)}"

def get_all_recipes() -> str:
    """Get all recipes available."""
    try:
        result = supabase.table("recipes").select("recipe_name, directions").execute()
        return f"Recipes: {result.data}"
    except Exception as e:
        return f"Error: {str(e)}"

def get_all_ingredients() -> str:
    """Get all ingredients/components available."""
    try:
        result = supabase.table("components").select("name, component_type").execute()
        return f"Components: {result.data}"
    except Exception as e:
        return f"Error: {str(e)}"

def get_recipe_details(recipe_name: str) -> str:
    """
    Get details for a specific recipe including ingredients.
    
    Args:
        recipe_name: Name of the recipe to look up
    """
    try:
        recipe = supabase.table("recipes").select("*").ilike("recipe_name", f"%{recipe_name}%").execute()
        if not recipe.data:
            return f"Recipe '{recipe_name}' not found"
        
        recipe_id = recipe.data[0]['recipe_id']
        ingredients = supabase.table("recipe_components").select("amount, unit, component_id").eq("recipe_id", recipe_id).execute()
        
        result_text = f"Recipe: {recipe.data[0]['recipe_name']}\n"
        result_text += f"Directions: {recipe.data[0]['directions']}\n"
        result_text += "Ingredients:\n"
        
        for ing in ingredients.data:
            comp = supabase.table("components").select("name").eq("component_id", ing['component_id']).execute()
            if comp.data:
                result_text += f"  - {ing['amount']} {ing['unit']} {comp.data[0]['name']}\n"
        
        return result_text
    except Exception as e:
        return f"Error: {str(e)}"

# Create tools list
tools = [get_all_users, get_all_kitchens, get_all_recipes, get_all_ingredients, get_recipe_details]

# Bind tools to LLM
llm_with_tools = llm.bind_tools(tools)

# Assistant node
def assistant(state: MessagesState):
    """The assistant node that can call tools or respond directly."""
    return {"messages": [llm_with_tools.invoke(state["messages"])]}

# Build the graph
builder = StateGraph(MessagesState)
builder.add_node("assistant", assistant)
builder.add_node("tools", ToolNode(tools))
builder.add_edge(START, "assistant")
builder.add_conditional_edges("assistant", tools_condition)
builder.add_edge("tools", "assistant")

# Compile and export the graph
agent = builder.compile()
