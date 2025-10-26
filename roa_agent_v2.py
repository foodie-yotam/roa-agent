"""
ROA Voice Agent - Neo4j Version
Optimized for recipe management based on foodweb.ai features
"""

import json
import os
from typing import Dict, List, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import AIMessage, ToolMessage
from langgraph.graph import StateGraph, MessagesState, START, END
from neo4j import GraphDatabase

# Neo4j connection (must come from environment)
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

missing = [name for name, value in (
    ("NEO4J_URI", NEO4J_URI),
    ("NEO4J_USER", NEO4J_USER),
    ("NEO4J_PASSWORD", NEO4J_PASSWORD),
) if not value]

if missing:
    raise RuntimeError(
        "Missing required Neo4j environment variables: " + ", ".join(missing)
    )

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

# LLM setup
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "AIzaSyAPxogxsFokL6Ty0mmlIn3YuP3-AtKSd5U")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
llm = ChatGoogleGenerativeAI(
    model=GEMINI_MODEL,
    google_api_key=GOOGLE_API_KEY,
    temperature=0
)

# ========== HELPER FUNCTIONS ==========
def run_query(query: str, parameters: dict = None):
    """Execute a Cypher query and return results"""
    with driver.session() as session:
        result = session.run(query, parameters or {})
        return [record.data() for record in result]

# ========== CORE ROA TOOLS (TOP 5) ==========

def search_recipes(kitchen_name: Optional[str] = None, recipe_name: Optional[str] = None) -> str:
    """
    Search for recipes in your kitchen. You can search by kitchen name, recipe name, or both.
    If no parameters provided, returns all recipes.
    
    Args:
        kitchen_name: Name of the kitchen (optional, e.g. "FoodWeb Internal", "Colmado Carpanta")
        recipe_name: Name or partial name of the recipe (optional, e.g. "Gazpacho", "Pasta")
    
    Returns:
        List of matching recipes with their basic info
    """
    try:
        if kitchen_name and recipe_name:
            # Search by both
            query = """
            MATCH (k:Kitchen {name: $kitchen_name})-[:HAS_RECIPE]->(r:Recipe)
            WHERE r.name CONTAINS $recipe_name
            RETURN k.name as kitchen, r.name as recipe, r.time_minutes as time
            ORDER BY r.name
            """
            results = run_query(query, {"kitchen_name": kitchen_name, "recipe_name": recipe_name})
        elif kitchen_name:
            # Search by kitchen only
            query = """
            MATCH (k:Kitchen {name: $kitchen_name})-[:HAS_RECIPE]->(r:Recipe)
            RETURN k.name as kitchen, r.name as recipe, r.time_minutes as time
            ORDER BY r.name
            """
            results = run_query(query, {"kitchen_name": kitchen_name})
        elif recipe_name:
            # Search by recipe name across all kitchens
            query = """
            MATCH (k:Kitchen)-[:HAS_RECIPE]->(r:Recipe)
            WHERE r.name CONTAINS $recipe_name
            RETURN k.name as kitchen, r.name as recipe, r.time_minutes as time
            ORDER BY k.name, r.name
            """
            results = run_query(query, {"recipe_name": recipe_name})
        else:
            # Return all recipes (limited to 20)
            query = """
            MATCH (k:Kitchen)-[:HAS_RECIPE]->(r:Recipe)
            RETURN k.name as kitchen, r.name as recipe, r.time_minutes as time
            ORDER BY k.name, r.name
            LIMIT 20
            """
            results = run_query(query)
        
        if not results:
            return "No recipes found matching your search."
        
        return f"Found {len(results)} recipe(s): {results}"
    except Exception as e:
        return f"Error searching recipes: {str(e)}"


def get_recipe_details(recipe_name: str, kitchen_name: Optional[str] = None) -> str:
    """
    Get complete details of a recipe including directions, ingredients, and sub-recipes.
    
    Args:
        recipe_name: Exact name of the recipe (e.g. "Gazpacho")
        kitchen_name: Kitchen name (optional, helps if recipe exists in multiple kitchens)
    
    Returns:
        Complete recipe with directions, cooking time, ingredients with amounts, and required sub-recipes
    """
    try:
        if kitchen_name:
            # Get recipe from specific kitchen
            query = """
            MATCH (k:Kitchen {name: $kitchen_name})-[:HAS_RECIPE]->(r:Recipe {name: $recipe_name})
            OPTIONAL MATCH (r)-[:IN_CATEGORY]->(cat:Category)
            OPTIONAL MATCH (r)-[u:USES]->(c:Component)
            OPTIONAL MATCH (r)-[req:REQUIRES]->(sub:Recipe)
            RETURN r.name as recipe,
                   r.directions as directions,
                   r.time_minutes as time_minutes,
                   cat.name as category,
                   collect(DISTINCT {name: c.name, type: c.type, amount: u.amount, unit: u.unit}) as ingredients,
                   collect(DISTINCT {name: sub.name, amount: req.amount, unit: req.unit}) as sub_recipes
            """
            results = run_query(query, {"kitchen_name": kitchen_name, "recipe_name": recipe_name})
        else:
            # Search across all kitchens
            query = """
            MATCH (k:Kitchen)-[:HAS_RECIPE]->(r:Recipe {name: $recipe_name})
            OPTIONAL MATCH (r)-[:IN_CATEGORY]->(cat:Category)
            OPTIONAL MATCH (r)-[u:USES]->(c:Component)
            OPTIONAL MATCH (r)-[req:REQUIRES]->(sub:Recipe)
            RETURN k.name as kitchen,
                   r.name as recipe,
                   r.directions as directions,
                   r.time_minutes as time_minutes,
                   cat.name as category,
                   collect(DISTINCT {name: c.name, type: c.type, amount: u.amount, unit: u.unit}) as ingredients,
                   collect(DISTINCT {name: sub.name, amount: req.amount, unit: req.unit}) as sub_recipes
            LIMIT 1
            """
            results = run_query(query, {"recipe_name": recipe_name})
        
        if not results:
            return f"Recipe '{recipe_name}' not found. Try searching first with search_recipes()."
        
        return f"Recipe details: {results}"
    except Exception as e:
        return f"Error getting recipe details: {str(e)}"


def create_recipe(recipe_name: str, kitchen_name: str, directions: List[str], 
                  time_minutes: Optional[int] = 30, category: Optional[str] = None) -> str:
    """
    Create a new recipe in your kitchen. You can add ingredients later with add_ingredient_to_recipe().
    
    Args:
        recipe_name: Name of the recipe (e.g. "Spaghetti Carbonara")
        kitchen_name: Which kitchen to add it to (e.g. "FoodWeb Internal")
        directions: List of cooking steps (e.g. ["Boil water", "Cook pasta", "Mix with sauce"])
        time_minutes: Cooking time in minutes (optional, default: 30)
        category: Recipe category (optional, e.g. "Main", "Dessert")
    
    Returns:
        Confirmation message with recipe details
    """
    try:
        # Check if kitchen exists
        kitchen_check = run_query("MATCH (k:Kitchen {name: $name}) RETURN k", {"name": kitchen_name})
        if not kitchen_check:
            return f"Kitchen '{kitchen_name}' not found. Available kitchens: {[k['k']['name'] for k in run_query('MATCH (k:Kitchen) RETURN k LIMIT 5')]}"
        
        query = """
        MATCH (k:Kitchen {name: $kitchen_name})
        CREATE (r:Recipe {
            recipe_id: randomUUID(),
            name: $recipe_name,
            directions: $directions,
            time_minutes: $time_minutes
        })
        CREATE (k)-[:HAS_RECIPE]->(r)
        """
        
        params = {
            "kitchen_name": kitchen_name,
            "recipe_name": recipe_name,
            "directions": directions,
            "time_minutes": time_minutes or 30
        }
        
        # Add category if provided
        if category:
            query += """
            WITH r, k
            MERGE (k)-[:HAS_CATEGORY]->(c:Category {name: $category})
            ON CREATE SET c.category_id = randomUUID()
            CREATE (r)-[:IN_CATEGORY]->(c)
            """
            params["category"] = category
        
        query += " RETURN r"
        results = run_query(query, params)
        
        return f"✅ Recipe '{recipe_name}' created in '{kitchen_name}'! Time: {time_minutes or 30} mins. Add ingredients with add_ingredient_to_recipe()."
    except Exception as e:
        return f"Error creating recipe: {str(e)}"


def add_ingredient_to_recipe(recipe_name: str, ingredient_name: str, amount: float, 
                             unit: str, kitchen_name: Optional[str] = None) -> str:
    """
    Add an ingredient to an existing recipe. Creates the ingredient if it doesn't exist.
    
    Args:
        recipe_name: Name of the recipe (e.g. "Gazpacho")
        ingredient_name: Name of the ingredient (e.g. "tomato", "olive oil")
        amount: Amount/quantity (e.g. 200, 2.5)
        unit: Unit of measurement (e.g. "g", "ml", "tbsp", "kg", "pieces")
        kitchen_name: Kitchen name (optional, required if recipe exists in multiple kitchens)
    
    Returns:
        Confirmation that ingredient was added
    """
    try:
        if kitchen_name:
            query = """
            MATCH (k:Kitchen {name: $kitchen_name})-[:HAS_RECIPE]->(r:Recipe {name: $recipe_name})
            MERGE (k)-[:HAS_COMPONENT]->(c:Component {name: $ingredient_name})
            ON CREATE SET c.component_id = randomUUID(), c.type = 'Raw_Ingredient'
            MERGE (r)-[u:USES]->(c)
            SET u.amount = $amount, u.unit = $unit
            RETURN r.name as recipe, c.name as ingredient, u.amount as amount, u.unit as unit
            """
            params = {
                "kitchen_name": kitchen_name,
                "recipe_name": recipe_name,
                "ingredient_name": ingredient_name,
                "amount": amount,
                "unit": unit
            }
        else:
            # Try to find recipe in any kitchen
            query = """
            MATCH (k:Kitchen)-[:HAS_RECIPE]->(r:Recipe {name: $recipe_name})
            MERGE (k)-[:HAS_COMPONENT]->(c:Component {name: $ingredient_name})
            ON CREATE SET c.component_id = randomUUID(), c.type = 'Raw_Ingredient'
            MERGE (r)-[u:USES]->(c)
            SET u.amount = $amount, u.unit = $unit
            RETURN r.name as recipe, c.name as ingredient, u.amount as amount, u.unit as unit
            LIMIT 1
            """
            params = {
                "recipe_name": recipe_name,
                "ingredient_name": ingredient_name,
                "amount": amount,
                "unit": unit
            }
        
        results = run_query(query, params)
        
        if not results:
            return f"Recipe '{recipe_name}' not found. Create it first with create_recipe()."
        
        return f"✅ Added {amount} {unit} of {ingredient_name} to {recipe_name}!"
    except Exception as e:
        return f"Error adding ingredient: {str(e)}"


def list_ingredients(kitchen_name: Optional[str] = None, search_term: Optional[str] = None) -> str:
    """
    List available ingredients/components in the kitchen inventory.
    
    Args:
        kitchen_name: Filter by kitchen (optional, e.g. "FoodWeb Internal")
        search_term: Search for specific ingredient (optional, e.g. "tomato")
    
    Returns:
        List of available ingredients with their types
    """
    try:
        if kitchen_name and search_term:
            query = """
            MATCH (k:Kitchen {name: $kitchen_name})-[:HAS_COMPONENT]->(c:Component)
            WHERE c.name CONTAINS $search_term
            RETURN c.name as ingredient, c.type as type
            ORDER BY c.name
            """
            results = run_query(query, {"kitchen_name": kitchen_name, "search_term": search_term})
        elif kitchen_name:
            query = """
            MATCH (k:Kitchen {name: $kitchen_name})-[:HAS_COMPONENT]->(c:Component)
            RETURN c.name as ingredient, c.type as type
            ORDER BY c.name
            LIMIT 50
            """
            results = run_query(query, {"kitchen_name": kitchen_name})
        elif search_term:
            query = """
            MATCH (c:Component)
            WHERE c.name CONTAINS $search_term
            RETURN c.name as ingredient, c.type as type
            ORDER BY c.name
            LIMIT 20
            """
            results = run_query(query, {"search_term": search_term})
        else:
            query = """
            MATCH (c:Component)
            RETURN c.name as ingredient, c.type as type
            ORDER BY c.name
            LIMIT 30
            """
            results = run_query(query)
        
        if not results:
            return "No ingredients found."
        
        return f"Found {len(results)} ingredient(s): {results}"
    except Exception as e:
        return f"Error listing ingredients: {str(e)}"


# ========== ADVANCED CRUD TOOLS ==========

def create_kitchen(kitchen_name: str, kitchen_type: str = "restaurant") -> str:
    """
    Create a new kitchen in the system.
    
    Args:
        kitchen_name: Name of the kitchen (e.g. "Staging Test Kitchen")
        kitchen_type: Type of kitchen (optional, e.g. "restaurant", "test", "catering")
    
    Returns:
        Confirmation message
    """
    try:
        query = """
        CREATE (k:Kitchen {
            kitchen_id: randomUUID(),
            name: $name,
            type: $type
        })
        RETURN k.name as name, k.type as type
        """
        results = run_query(query, {"name": kitchen_name, "type": kitchen_type})
        return f"✅ Kitchen '{kitchen_name}' created (type: {kitchen_type})!"
    except Exception as e:
        return f"Error creating kitchen: {str(e)}"


def list_kitchens() -> str:
    """
    List all kitchens in the system.
    
    Returns:
        List of all kitchens with their types
    """
    try:
        query = """
        MATCH (k:Kitchen)
        RETURN k.name as name, k.type as type
        ORDER BY k.name
        """
        results = run_query(query)
        if not results:
            return "No kitchens found. Create one with create_kitchen()."
        return f"Found {len(results)} kitchen(s): {results}"
    except Exception as e:
        return f"Error listing kitchens: {str(e)}"


def delete_kitchen(kitchen_name: str) -> str:
    """
    Delete a kitchen and all its associated data (recipes, categories, components).
    
    Args:
        kitchen_name: Name of the kitchen to delete
    
    Returns:
        Confirmation message
    """
    try:
        query = """
        MATCH (k:Kitchen {name: $name})
        OPTIONAL MATCH (k)-[r]-()
        DELETE r, k
        RETURN count(k) as deleted
        """
        results = run_query(query, {"name": kitchen_name})
        if results and results[0]["deleted"] > 0:
            return f"✅ Kitchen '{kitchen_name}' and all its data deleted!"
        return f"Kitchen '{kitchen_name}' not found."
    except Exception as e:
        return f"Error deleting kitchen: {str(e)}"


def update_recipe(recipe_name: str, kitchen_name: str, 
                  new_directions: Optional[List[str]] = None,
                  new_time_minutes: Optional[int] = None,
                  new_notes: Optional[str] = None) -> str:
    """
    Update an existing recipe's details.
    
    Args:
        recipe_name: Name of the recipe to update
        kitchen_name: Kitchen where the recipe exists
        new_directions: New cooking directions (optional)
        new_time_minutes: New cooking time (optional)
        new_notes: New notes (optional)
    
    Returns:
        Confirmation message
    """
    try:
        updates = []
        params = {"recipe_name": recipe_name, "kitchen_name": kitchen_name}
        
        if new_directions is not None:
            updates.append("r.directions = $new_directions")
            params["new_directions"] = new_directions
        if new_time_minutes is not None:
            updates.append("r.time_minutes = $new_time_minutes")
            params["new_time_minutes"] = new_time_minutes
        if new_notes is not None:
            updates.append("r.notes = $new_notes")
            params["new_notes"] = new_notes
        
        if not updates:
            return "No updates provided. Specify at least one field to update."
        
        query = f"""
        MATCH (k:Kitchen {{name: $kitchen_name}})-[:HAS_RECIPE]->(r:Recipe {{name: $recipe_name}})
        SET {', '.join(updates)}
        RETURN r.name as recipe
        """
        results = run_query(query, params)
        
        if not results:
            return f"Recipe '{recipe_name}' not found in '{kitchen_name}'."
        return f"✅ Recipe '{recipe_name}' updated successfully!"
    except Exception as e:
        return f"Error updating recipe: {str(e)}"


def delete_recipe(recipe_name: str, kitchen_name: str) -> str:
    """
    Delete a recipe from a kitchen.
    
    Args:
        recipe_name: Name of the recipe to delete
        kitchen_name: Kitchen where the recipe exists
    
    Returns:
        Confirmation message
    """
    try:
        query = """
        MATCH (k:Kitchen {name: $kitchen_name})-[:HAS_RECIPE]->(r:Recipe {name: $recipe_name})
        OPTIONAL MATCH (r)-[rel]-()
        DELETE rel, r
        RETURN count(r) as deleted
        """
        results = run_query(query, {"recipe_name": recipe_name, "kitchen_name": kitchen_name})
        if results and results[0]["deleted"] > 0:
            return f"✅ Recipe '{recipe_name}' deleted from '{kitchen_name}'!"
        return f"Recipe '{recipe_name}' not found in '{kitchen_name}'."
    except Exception as e:
        return f"Error deleting recipe: {str(e)}"


def remove_ingredient_from_recipe(recipe_name: str, ingredient_name: str, 
                                   kitchen_name: Optional[str] = None) -> str:
    """
    Remove an ingredient from a recipe.
    
    Args:
        recipe_name: Name of the recipe
        ingredient_name: Name of the ingredient to remove
        kitchen_name: Kitchen name (optional)
    
    Returns:
        Confirmation message
    """
    try:
        if kitchen_name:
            query = """
            MATCH (k:Kitchen {name: $kitchen_name})-[:HAS_RECIPE]->(r:Recipe {name: $recipe_name})
            MATCH (r)-[u:USES]->(c:Component {name: $ingredient_name})
            DELETE u
            RETURN r.name as recipe, c.name as ingredient
            """
            params = {"kitchen_name": kitchen_name, "recipe_name": recipe_name, "ingredient_name": ingredient_name}
        else:
            query = """
            MATCH (k:Kitchen)-[:HAS_RECIPE]->(r:Recipe {name: $recipe_name})
            MATCH (r)-[u:USES]->(c:Component {name: $ingredient_name})
            DELETE u
            RETURN r.name as recipe, c.name as ingredient
            LIMIT 1
            """
            params = {"recipe_name": recipe_name, "ingredient_name": ingredient_name}
        
        results = run_query(query, params)
        if not results:
            return f"Ingredient '{ingredient_name}' not found in recipe '{recipe_name}'."
        return f"✅ Removed {ingredient_name} from {recipe_name}!"
    except Exception as e:
        return f"Error removing ingredient: {str(e)}"


def update_ingredient_amount(recipe_name: str, ingredient_name: str, 
                             new_amount: float, new_unit: str,
                             kitchen_name: Optional[str] = None) -> str:
    """
    Update the amount/unit of an ingredient in a recipe.
    
    Args:
        recipe_name: Name of the recipe
        ingredient_name: Name of the ingredient
        new_amount: New amount
        new_unit: New unit
        kitchen_name: Kitchen name (optional)
    
    Returns:
        Confirmation message
    """
    try:
        if kitchen_name:
            query = """
            MATCH (k:Kitchen {name: $kitchen_name})-[:HAS_RECIPE]->(r:Recipe {name: $recipe_name})
            MATCH (r)-[u:USES]->(c:Component {name: $ingredient_name})
            SET u.amount = $new_amount, u.unit = $new_unit
            RETURN r.name as recipe, c.name as ingredient, u.amount as amount, u.unit as unit
            """
            params = {
                "kitchen_name": kitchen_name,
                "recipe_name": recipe_name,
                "ingredient_name": ingredient_name,
                "new_amount": new_amount,
                "new_unit": new_unit
            }
        else:
            query = """
            MATCH (k:Kitchen)-[:HAS_RECIPE]->(r:Recipe {name: $recipe_name})
            MATCH (r)-[u:USES]->(c:Component {name: $ingredient_name})
            SET u.amount = $new_amount, u.unit = $new_unit
            RETURN r.name as recipe, c.name as ingredient, u.amount as amount, u.unit as unit
            LIMIT 1
            """
            params = {
                "recipe_name": recipe_name,
                "ingredient_name": ingredient_name,
                "new_amount": new_amount,
                "new_unit": new_unit
            }
        
        results = run_query(query, params)
        if not results:
            return f"Ingredient '{ingredient_name}' not found in recipe '{recipe_name}'."
        return f"✅ Updated {ingredient_name} in {recipe_name} to {new_amount} {new_unit}!"
    except Exception as e:
        return f"Error updating ingredient amount: {str(e)}"


def create_category(category_name: str, kitchen_name: str) -> str:
    """
    Create a new category in a kitchen.
    
    Args:
        category_name: Name of the category (e.g. "Desserts", "Main Dishes")
        kitchen_name: Kitchen to add the category to
    
    Returns:
        Confirmation message
    """
    try:
        query = """
        MATCH (k:Kitchen {name: $kitchen_name})
        MERGE (k)-[:HAS_CATEGORY]->(c:Category {name: $category_name})
        ON CREATE SET c.category_id = randomUUID()
        RETURN c.name as category
        """
        results = run_query(query, {"category_name": category_name, "kitchen_name": kitchen_name})
        if not results:
            return f"Kitchen '{kitchen_name}' not found."
        return f"✅ Category '{category_name}' created in '{kitchen_name}'!"
    except Exception as e:
        return f"Error creating category: {str(e)}"


def list_categories(kitchen_name: Optional[str] = None) -> str:
    """
    List all categories, optionally filtered by kitchen.
    
    Args:
        kitchen_name: Filter by kitchen (optional)
    
    Returns:
        List of categories
    """
    try:
        if kitchen_name:
            query = """
            MATCH (k:Kitchen {name: $kitchen_name})-[:HAS_CATEGORY]->(c:Category)
            RETURN c.name as category
            ORDER BY c.name
            """
            results = run_query(query, {"kitchen_name": kitchen_name})
        else:
            query = """
            MATCH (c:Category)
            RETURN c.name as category
            ORDER BY c.name
            """
            results = run_query(query)
        
        if not results:
            return "No categories found."
        return f"Found {len(results)} categor{'y' if len(results) == 1 else 'ies'}: {results}"
    except Exception as e:
        return f"Error listing categories: {str(e)}"


def assign_recipe_to_category(recipe_name: str, category_name: str, kitchen_name: str) -> str:
    """
    Assign a recipe to a category.
    
    Args:
        recipe_name: Name of the recipe
        category_name: Name of the category
        kitchen_name: Kitchen where both exist
    
    Returns:
        Confirmation message
    """
    try:
        query = """
        MATCH (k:Kitchen {name: $kitchen_name})-[:HAS_RECIPE]->(r:Recipe {name: $recipe_name})
        MATCH (k)-[:HAS_CATEGORY]->(c:Category {name: $category_name})
        MERGE (r)-[:IN_CATEGORY]->(c)
        RETURN r.name as recipe, c.name as category
        """
        results = run_query(query, {
            "recipe_name": recipe_name,
            "category_name": category_name,
            "kitchen_name": kitchen_name
        })
        if not results:
            return f"Recipe '{recipe_name}' or category '{category_name}' not found in '{kitchen_name}'."
        return f"✅ Recipe '{recipe_name}' assigned to category '{category_name}'!"
    except Exception as e:
        return f"Error assigning recipe to category: {str(e)}"


def delete_component(component_name: str, kitchen_name: str) -> str:
    """
    Delete a component/ingredient from a kitchen (removes all recipe associations).
    
    Args:
        component_name: Name of the component to delete
        kitchen_name: Kitchen where the component exists
    
    Returns:
        Confirmation message
    """
    try:
        query = """
        MATCH (k:Kitchen {name: $kitchen_name})-[:HAS_COMPONENT]->(c:Component {name: $component_name})
        OPTIONAL MATCH (c)-[r]-()
        DELETE r, c
        RETURN count(c) as deleted
        """
        results = run_query(query, {"component_name": component_name, "kitchen_name": kitchen_name})
        if results and results[0]["deleted"] > 0:
            return f"✅ Component '{component_name}' deleted from '{kitchen_name}'!"
        return f"Component '{component_name}' not found in '{kitchen_name}'."
    except Exception as e:
        return f"Error deleting component: {str(e)}"


def _build_tool_registry(tool_functions: List):
    """Create a mapping from tool name to callable."""
    registry: Dict[str, callable] = {}
    for tool in tool_functions:
        name = getattr(tool, "__name__", None)
        if not name:
            raise ValueError("Tool functions must have a __name__ attribute")
        registry[name] = tool
    return registry


# Create tools list (5 high-level + 13 advanced CRUD tools = 18 total)
tools = [
    # High-level tools (quick access)
    search_recipes,
    get_recipe_details,
    create_recipe,
    add_ingredient_to_recipe,
    list_ingredients,
    
    # Advanced CRUD tools
    # Kitchen management
    create_kitchen,
    list_kitchens,
    delete_kitchen,
    
    # Recipe management
    update_recipe,
    delete_recipe,
    
    # Ingredient/Component management
    remove_ingredient_from_recipe,
    update_ingredient_amount,
    delete_component,
    
    # Category management
    create_category,
    list_categories,
    assign_recipe_to_category,
]

# Tool registry for direct invocation
tool_registry = _build_tool_registry(tools)

# Bind tools to LLM
llm_with_tools = llm.bind_tools(tools)

# System prompt
SYSTEM_PROMPT = """You are ROA, an AI culinary assistant for professional kitchens.

Your role is to help chefs manage recipes, ingredients, and kitchen operations efficiently.

Key capabilities:
- **Quick Access**: Search recipes, get details, create recipes, add ingredients, list inventory
- **Kitchen Management**: Create, list, and delete kitchens
- **Recipe Management**: Create, update, delete recipes and assign them to categories
- **Ingredient Management**: Add, update amounts, remove ingredients from recipes
- **Category Management**: Create categories, list them, and organize recipes
- **Full CRUD**: Complete control over all kitchen data (kitchens, recipes, ingredients, categories)

Always be concise and professional. When a chef asks for a recipe, provide clear, actionable information.
If they want to create or modify recipes, guide them through the process step by step.

For recipe searches, if no kitchen is specified, search across all kitchens.
Always confirm successful actions with a brief, clear message."""

# Assistant node
def assistant(state: MessagesState):
    """The assistant node that can call tools or respond directly."""
    messages = state["messages"]
    
    # Add system prompt if this is the first message
    if len(messages) == 1:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages
    
    return {"messages": [llm_with_tools.invoke(messages)]}


def should_call_tools(state: MessagesState) -> str:
    """Route to tool execution when the assistant requested a tool."""
    messages = state["messages"]
    if not messages:
        return "end"

    last = messages[-1]
    if isinstance(last, AIMessage) and last.tool_calls:
        return "tools"
    return "end"


def execute_tools(state: MessagesState):
    """Execute requested tools and return ToolMessage responses."""
    messages = state["messages"]
    last = messages[-1]
    tool_messages = []

    if not isinstance(last, AIMessage) or not last.tool_calls:
        return {"messages": []}

    for call in last.tool_calls:
        tool_name = call.get("name")
        tool = tool_registry.get(tool_name)
        tool_call_id = call.get("id")

        if tool is None:
            tool_messages.append(
                ToolMessage(
                    content=f"Tool '{tool_name}' is not available.",
                    name=tool_name or "unknown",
                    tool_call_id=tool_call_id,
                )
            )
            continue

        args = call.get("args") or {}
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except json.JSONDecodeError:
                args = {}

        try:
            result = tool(**args)
        except TypeError as exc:
            result = f"Error calling tool '{tool_name}': {exc}"

        tool_messages.append(
            ToolMessage(
                content=str(result),
                name=tool_name,
                tool_call_id=tool_call_id,
            )
        )

    return {"messages": tool_messages}

# Build the graph
builder = StateGraph(MessagesState)
builder.add_node("assistant", assistant)
builder.add_node("tools", execute_tools)
builder.add_edge(START, "assistant")
builder.add_conditional_edges(
    "assistant",
    should_call_tools,
    {
        "tools": "tools",
        "end": END,
    },
)
builder.add_edge("tools", "assistant")

# Compile and export the graph
agent = builder.compile()
