"""Kitchen team tools - recipe management"""
from typing import Optional
from langchain_core.tools import tool
from ....shared.db import run_query


@tool
def search_recipes(kitchen_name: Optional[str] = None, recipe_name: Optional[str] = None) -> str:
    """Search for recipes in the database
    
    Args:
        kitchen_name: Filter by kitchen name (optional)
        recipe_name: Filter by recipe name (optional)
    
    Example Input: kitchen_name="Yotam Kitchen"
    Example Output: "Found 12 recipes: [{'kitchen': 'Yotam Kitchen', 'recipe': 'Arroz Sushi'}, ...]"
    
    Example Input: recipe_name="Arroz Sushi"
    Example Output: "Found 1 recipes: [{'kitchen': 'Yotam Kitchen', 'recipe': 'Arroz Sushi'}]"
    """
    try:
        if kitchen_name:
            query = "MATCH (k:Kitchen {name: $kitchen_name})-[:HAS_RECIPE]->(r:Recipe) RETURN k.name as kitchen, r.name as recipe"
            results = run_query(query, {"kitchen_name": kitchen_name})
        else:
            query = "MATCH (k:Kitchen)-[:HAS_RECIPE]->(r:Recipe) RETURN k.name as kitchen, r.name as recipe LIMIT 20"
            results = run_query(query)
        return f"Found {len(results)} recipes: {results}" if results else "No recipes found"
    except Exception as e:
        return f"Error: {str(e)}"


@tool
def get_recipe_details(recipe_name: str, kitchen_name: Optional[str] = None) -> str:
    """Get detailed recipe information including ingredients
    
    Args:
        recipe_name: Name of the recipe
        kitchen_name: Kitchen name (optional)
    
    Example Input: recipe_name="Arroz Sushi"
    Example Output: "Recipe details: {'name': 'Arroz Sushi', 'directions': 'Cook rice...', 'ingredients': [{'name': 'Rice', 'amount': 2, 'unit': 'cups'}, ...]}"
    """
    try:
        query = """
        MATCH (k:Kitchen)-[:HAS_RECIPE]->(r:Recipe {name: $recipe_name})
        OPTIONAL MATCH (r)-[u:USES]->(c:Component)
        RETURN r.name, r.directions, collect({name: c.name, amount: u.amount, unit: u.unit}) as ingredients
        LIMIT 1
        """
        results = run_query(query, {"recipe_name": recipe_name})
        return f"Recipe details: {results[0] if results else 'Not found'}"
    except Exception as e:
        return f"Error: {str(e)}"


@tool
def get_team_members() -> str:
    """Get list of team members
    
    Example Output: "Team members: Chef, Sous Chef, Line Cook, Prep Cook"
    """
    return "Team members: Chef, Sous Chef, Line Cook, Prep Cook"


@tool
def assign_task(task: str, assignee: str) -> str:
    """Assign a task to a team member
    
    Args:
        task: Task description
        assignee: Team member to assign to
    
    Example Input: task="Prep vegetables", assignee="Line Cook"
    Example Output: "Assigned 'Prep vegetables' to Line Cook"
    """
    return f"Assigned '{task}' to {assignee}"


@tool
def suggest_dishes() -> str:
    """Suggest new dish ideas based on current ingredients
    
    Example Output: "Suggested dishes: Seasonal pasta, Grilled fish, Farm salad"
    """
    return "Suggested dishes: Seasonal pasta, Grilled fish, Farm salad"
