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

# ========== RECIPE CRUD ==========
def get_all_recipes() -> str:
    """Get all recipes available."""
    try:
        result = supabase.table("recipes").select("*").execute()
        return f"Recipes: {result.data}"
    except Exception as e:
        return f"Error: {str(e)}"

def create_recipe(recipe_name: str, directions: str, kitchen_id: str, category_id: str = None) -> str:
    """Create a new recipe."""
    try:
        result = supabase.table("recipes").insert({
            "recipe_name": recipe_name,
            "directions": directions,
            "kitchen_id": kitchen_id,
            "category_id": category_id
        }).execute()
        return f"Recipe created: {result.data}"
    except Exception as e:
        return f"Error: {str(e)}"

def update_recipe(recipe_id: str, recipe_name: str = None, directions: str = None) -> str:
    """Update an existing recipe."""
    try:
        updates = {}
        if recipe_name: updates["recipe_name"] = recipe_name
        if directions: updates["directions"] = directions
        result = supabase.table("recipes").update(updates).eq("recipe_id", recipe_id).execute()
        return f"Recipe updated: {result.data}"
    except Exception as e:
        return f"Error: {str(e)}"

def delete_recipe(recipe_id: str) -> str:
    """Delete a recipe."""
    try:
        result = supabase.table("recipes").delete().eq("recipe_id", recipe_id).execute()
        return f"Recipe deleted"
    except Exception as e:
        return f"Error: {str(e)}"

# ========== COMPONENT CRUD ==========
def get_all_components() -> str:
    """Get all ingredients and tools."""
    try:
        result = supabase.table("components").select("*").execute()
        return f"Components: {result.data}"
    except Exception as e:
        return f"Error: {str(e)}"

def create_component(name: str, component_type: str, kitchen_id: str) -> str:
    """Create a new ingredient or tool. component_type must be 'ingredient' or 'tool'."""
    try:
        result = supabase.table("components").insert({
            "name": name,
            "component_type": component_type,
            "kitchen_id": kitchen_id
        }).execute()
        return f"Component created: {result.data}"
    except Exception as e:
        return f"Error: {str(e)}"

def update_component(component_id: str, name: str = None) -> str:
    """Update a component name."""
    try:
        updates = {}
        if name: updates["name"] = name
        result = supabase.table("components").update(updates).eq("component_id", component_id).execute()
        return f"Component updated: {result.data}"
    except Exception as e:
        return f"Error: {str(e)}"

def delete_component(component_id: str) -> str:
    """Delete a component."""
    try:
        result = supabase.table("components").delete().eq("component_id", component_id).execute()
        return f"Component deleted"
    except Exception as e:
        return f"Error: {str(e)}"

# ========== CATEGORY CRUD ==========
def get_all_categories() -> str:
    """Get all recipe categories."""
    try:
        result = supabase.table("categories").select("*").execute()
        return f"Categories: {result.data}"
    except Exception as e:
        return f"Error: {str(e)}"

def create_category(name: str, kitchen_id: str) -> str:
    """Create a new recipe category."""
    try:
        result = supabase.table("categories").insert({
            "name": name,
            "kitchen_id": kitchen_id
        }).execute()
        return f"Category created: {result.data}"
    except Exception as e:
        return f"Error: {str(e)}"

def update_category(category_id: str, name: str) -> str:
    """Update a category name."""
    try:
        result = supabase.table("categories").update({"name": name}).eq("category_id", category_id).execute()
        return f"Category updated: {result.data}"
    except Exception as e:
        return f"Error: {str(e)}"

def delete_category(category_id: str) -> str:
    """Delete a category."""
    try:
        result = supabase.table("categories").delete().eq("category_id", category_id).execute()
        return f"Category deleted"
    except Exception as e:
        return f"Error: {str(e)}"

# ========== KITCHEN CRUD ==========
def get_all_kitchens() -> str:
    """Get all kitchens."""
    try:
        result = supabase.table("kitchen").select("*").execute()
        return f"Kitchens: {result.data}"
    except Exception as e:
        return f"Error: {str(e)}"

def create_kitchen(name: str, kitchen_type: str) -> str:
    """Create a new kitchen."""
    try:
        result = supabase.table("kitchen").insert({
            "name": name,
            "type": kitchen_type
        }).execute()
        return f"Kitchen created: {result.data}"
    except Exception as e:
        return f"Error: {str(e)}"

def update_kitchen(kitchen_id: str, name: str = None, kitchen_type: str = None) -> str:
    """Update kitchen details."""
    try:
        updates = {}
        if name: updates["name"] = name
        if kitchen_type: updates["type"] = kitchen_type
        result = supabase.table("kitchen").update(updates).eq("kitchen_id", kitchen_id).execute()
        return f"Kitchen updated: {result.data}"
    except Exception as e:
        return f"Error: {str(e)}"

def delete_kitchen(kitchen_id: str) -> str:
    """Delete a kitchen."""
    try:
        result = supabase.table("kitchen").delete().eq("kitchen_id", kitchen_id).execute()
        return f"Kitchen deleted"
    except Exception as e:
        return f"Error: {str(e)}"

# ========== USER CRUD ==========
def get_all_users() -> str:
    """Get all users."""
    try:
        result = supabase.table("users").select("*").execute()
        return f"Users: {result.data}"
    except Exception as e:
        return f"Error: {str(e)}"

def create_user(fullname: str, email: str) -> str:
    """Create a new user."""
    try:
        result = supabase.table("users").insert({
            "user_fullname": fullname,
            "user_email": email
        }).execute()
        return f"User created: {result.data}"
    except Exception as e:
        return f"Error: {str(e)}"

def update_user(user_id: str, fullname: str = None, email: str = None) -> str:
    """Update user details."""
    try:
        updates = {}
        if fullname: updates["user_fullname"] = fullname
        if email: updates["user_email"] = email
        result = supabase.table("users").update(updates).eq("user_id", user_id).execute()
        return f"User updated: {result.data}"
    except Exception as e:
        return f"Error: {str(e)}"

def delete_user(user_id: str) -> str:
    """Delete a user."""
    try:
        result = supabase.table("users").delete().eq("user_id", user_id).execute()
        return f"User deleted"
    except Exception as e:
        return f"Error: {str(e)}"

# Create tools list with all CRUD operations
tools = [
    # Recipe CRUD
    get_all_recipes, create_recipe, update_recipe, delete_recipe,
    # Component CRUD
    get_all_components, create_component, update_component, delete_component,
    # Category CRUD
    get_all_categories, create_category, update_category, delete_category,
    # Kitchen CRUD
    get_all_kitchens, create_kitchen, update_kitchen, delete_kitchen,
    # User CRUD
    get_all_users, create_user, update_user, delete_user
]

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
