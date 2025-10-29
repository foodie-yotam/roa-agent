"""
ROA Agent Garden v3 - Hierarchical Multi-Agent System
Based on LangGraph hierarchical teams pattern

Hierarchical Structure:
ROOT SUPERVISOR
├── speaker_team (compiled subgraph)
│   ├── voice_agent
│   ├── video_agent
│   └── marketing_agent
├── builder_team (compiled subgraph - dev only)
│   └── dev_tools_agent
└── chef_team (compiled subgraph)
    ├── kitchen_team (compiled subgraph)
    │   ├── recipe_agent
    │   ├── team_pm_agent
    │   └── dish_ideation_agent
    ├── inventory_team (compiled subgraph)
    │   ├── stock_agent
    │   ├── suppliers_agent
    │   └── analysis_agent
    └── sales_team (compiled subgraph)
        └── profit_agent
"""

import os
from typing import List, Optional, Literal
from typing_extensions import TypedDict
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.types import Command
from neo4j import GraphDatabase

# ========== CONFIGURATION ==========
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "AIzaSyAPxogxsFokL6Ty0mmlIn3YuP3-AtKSd5U")

missing = [name for name, value in (
    ("NEO4J_URI", NEO4J_URI),
    ("NEO4J_USER", NEO4J_USER),
    ("NEO4J_PASSWORD", NEO4J_PASSWORD),
) if not value]

if missing:
    raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    google_api_key=GOOGLE_API_KEY,
    temperature=0,
    max_retries=3,
    timeout=60
)

# ========== HELPER FUNCTIONS ==========
def run_query(query: str, parameters: dict = None):
    """Execute a Cypher query and return results"""
    try:
        with driver.session() as session:
            result = session.run(query, parameters or {})
            return [record.data() for record in result]
    except Exception as e:
        return f"Database error: {str(e)}"


# ========== STATE DEFINITION ==========
class State(MessagesState):
    """State shared across all hierarchical levels"""
    next: str


# ========== SUPERVISOR HELPER ==========
def make_supervisor_node(llm, members: list[str]):
    """Create a supervisor node that routes to team members"""
    options = ["FINISH"] + members
    system_prompt = (
        f"You are a supervisor managing these workers: {members}. "
        "Based on the conversation history and the user's request:\n"
        "1. If a worker has already completed the task successfully, respond with FINISH\n"
        "2. If the task requires a specific worker, route to that worker\n"
        "3. IMPORTANT: Each worker should only be called ONCE per task unless explicitly needed again\n"
        "4. Look at recent messages - if a worker just responded, the task is likely complete\n"
        "Respond with the worker name to act next, or FINISH if done."
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


# ========================================================================
# TIER 3: TOOLS (organized by domain)
# ========================================================================

# --- Voice Tools ---
@tool
def generate_voice_response(text: str, tone: str = "professional") -> str:
    """Generate a voice-optimized text response"""
    return f"VOICE [{tone}]: {text}"

@tool
def text_to_speech(text: str) -> str:
    """Convert text to speech format"""
    return f"TTS: {text[:50]}..."

# --- Video Tools ---
@tool
def display_recipes(recipes: List[str]) -> str:
    """Display recipe cards in visual format with React Flow.
    
    Args:
        recipes: List of recipe names to display
    
    Returns:
        Text response with embedded visualization JSON
    """
    import json
    viz_json = json.dumps({
        "tool": "display_recipes",
        "params": {"recipes": recipes}
    })
    return f"Here are the recipes: {', '.join(recipes)}. VISUALIZATION: {viz_json}"

@tool
def display_multiplication(recipe: str, factor: int) -> str:
    """Show recipe scaling visualization with animated flow diagram.
    
    Args:
        recipe: Recipe name to scale
        factor: Multiplication factor (e.g., 3 for 3x)
    
    Returns:
        Text response with embedded visualization JSON
    """
    import json
    viz_json = json.dumps({
        "tool": "display_multiplication",
        "params": {"recipe": recipe, "factor": factor}
    })
    return f"I'll scale {recipe} by {factor}x. VISUALIZATION: {viz_json}"

@tool
def display_prediction_graph(metric: str, days: int = 30) -> str:
    """Display prediction/forecast trend graph.
    
    Args:
        metric: Metric to forecast (e.g., "sales", "inventory")
        days: Number of days to forecast
    
    Returns:
        Text response with embedded visualization JSON
    """
    import json
    viz_json = json.dumps({
        "tool": "display_prediction_graph",
        "params": {"metric": metric, "days": days}
    })
    return f"Here's the {metric} forecast for the next {days} days. VISUALIZATION: {viz_json}"

@tool
def display_inventory_alert(item: str, quantity: int) -> str:
    """Show low stock inventory alert visualization.
    
    Args:
        item: Item name that's low in stock
        quantity: Current quantity remaining
    
    Returns:
        Text response with embedded visualization JSON
    """
    import json
    viz_json = json.dumps({
        "tool": "display_inventory_alert",
        "params": {"item": item, "quantity": quantity}
    })
    return f"⚠️ Low stock alert: {item} has only {quantity} units remaining. Please reorder soon. VISUALIZATION: {viz_json}"

@tool
def display_team_assignment(task: str, assignee: str) -> str:
    """Show team task assignment visualization.
    
    Args:
        task: Task description
        assignee: Person assigned to the task
    
    Returns:
        Text response with embedded visualization JSON
    """
    import json
    viz_json = json.dumps({
        "tool": "display_team_assignment",
        "params": {"task": task, "assignee": assignee}
    })
    return f"I've assigned '{task}' to {assignee}. VISUALIZATION: {viz_json}"

# --- Marketing Tools ---
@tool
def create_marketing_content(product: str) -> str:
    """Generate marketing copy"""
    return f"MARKETING: Premium {product} - crafted with care"

# --- Builder Tools ---
@tool
def generate_tool_code(tool_name: str, description: str) -> str:
    """Generate Python tool code"""
    return f"CODE: @tool\\ndef {tool_name}(): pass  # {description}"

# --- Recipe Tools (REAL - from v2) ---
@tool
def search_recipes(kitchen_name: Optional[str] = None, recipe_name: Optional[str] = None) -> str:
    """Search for recipes"""
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
    """Get recipe details"""
    try:
        query = """
        MATCH (k:Kitchen)-[:HAS_RECIPE]->(r:Recipe {name: $recipe_name})
        OPTIONAL MATCH (r)-[u:USES]->(c:Component)
        RETURN r.name, r.directions, collect({name: c.name, amount: u.amount, unit: u.unit}) as ingredients
        LIMIT 1
        """
        results = run_query(query, {"recipe_name": recipe_name})
        return f"Recipe: {results}" if results else "Recipe not found"
    except Exception as e:
        return f"Error: {str(e)}"

# --- Team PM Tools ---
@tool
def get_team_members(kitchen_name: str) -> str:
    """Get team members"""
    try:
        query = "MATCH (u:User)-[:MEMBER_OF]->(k:Kitchen {name: $kitchen_name}) RETURN u.fullname"
        results = run_query(query, {"kitchen_name": kitchen_name})
        return f"Team: {results}"
    except Exception as e:
        return f"Error: {str(e)}"

@tool
def assign_task(member: str, task: str) -> str:
    """Assign task to member"""
    return f"ASSIGNED: {task} to {member}"

# --- Dish Ideation Tools ---
@tool
def suggest_dishes(ingredients: List[str]) -> str:
    """Suggest dish ideas"""
    return f"SUGGESTIONS: Try pasta, stir-fry, or salad with {', '.join(ingredients[:3])}"

# --- Stock Tools ---
@tool
def check_stock(kitchen_name: str, item: str = None) -> str:
    """Check stock levels"""
    if item:
        return f"STOCK: {item} - 50 units (Low)"
    return f"STOCK: 15 items in stock, 3 low"

# --- Supplier Tools ---
@tool
def list_suppliers() -> str:
    """List suppliers"""
    return "SUPPLIERS: FreshFarms, SeafoodDirect, ButcherPro"

# --- Analysis Tools ---
@tool
def forecast_demand(item: str, days: int = 7) -> str:
    """Forecast demand"""
    return f"FORECAST: {item} - need 20kg in {days} days"

# --- Profit Tools ---
@tool
def calculate_cost(recipe_name: str) -> str:
    """Calculate recipe cost"""
    return f"COST: {recipe_name} - $12.50/serving"


# ========================================================================
# TIER 2: WORKER AGENTS
# ========================================================================

# Speaker team workers
voice_agent = create_react_agent(
    llm, 
    [generate_voice_response, text_to_speech],
    prompt="You are the Voice Response Specialist. Generate clear voice-optimized responses."
)

video_agent = create_react_agent(
    llm, 
    [display_recipes, display_multiplication, display_prediction_graph, display_inventory_alert, display_team_assignment],
    prompt="You are the Video Visualization Specialist. Create visual displays using React Flow. Return visualization commands as JSON."
)

marketing_agent = create_react_agent(
    llm, 
    [create_marketing_content],
    prompt="You are the Marketing Specialist. Create compelling marketing content."
)

# Builder team workers
dev_tools_agent = create_react_agent(llm, [generate_tool_code])

# Kitchen team workers
recipe_agent = create_react_agent(llm, [search_recipes, get_recipe_details])
team_pm_agent = create_react_agent(llm, [get_team_members, assign_task])
dish_ideation_agent = create_react_agent(llm, [suggest_dishes])

# Inventory team workers
stock_agent = create_react_agent(llm, [check_stock])
suppliers_agent = create_react_agent(llm, [list_suppliers])
analysis_agent = create_react_agent(llm, [forecast_demand])

# Sales team workers
profit_agent = create_react_agent(llm, [calculate_cost])


# ========================================================================
# TIER 1.5: TEAM GRAPHS (Subgraphs with their own supervisors)
# ========================================================================

# === SPEAKER TEAM ===
def voice_node(state: State) -> Command[Literal["supervisor"]]:
    result = voice_agent.invoke(state)
    return Command(
        update={"messages": [HumanMessage(content=result["messages"][-1].content, name="voice")]},
        goto="supervisor"
    )

def video_node(state: State) -> Command[Literal["supervisor"]]:
    result = video_agent.invoke(state)
    return Command(
        update={"messages": [HumanMessage(content=result["messages"][-1].content, name="video")]},
        goto="supervisor"
    )

def marketing_node(state: State) -> Command[Literal["supervisor"]]:
    result = marketing_agent.invoke(state)
    return Command(
        update={"messages": [HumanMessage(content=result["messages"][-1].content, name="marketing")]},
        goto="supervisor"
    )

speaker_supervisor = make_supervisor_node(llm, ["voice", "video", "marketing"])

speaker_builder = StateGraph(State)
speaker_builder.add_node("supervisor", speaker_supervisor)
speaker_builder.add_node("voice", voice_node)
speaker_builder.add_node("video", video_node)
speaker_builder.add_node("marketing", marketing_node)
speaker_builder.add_edge(START, "supervisor")
speaker_team_graph = speaker_builder.compile()


# === BUILDER TEAM ===
def dev_tools_node(state: State) -> Command[Literal["supervisor"]]:
    result = dev_tools_agent.invoke(state)
    return Command(
        update={"messages": [HumanMessage(content=result["messages"][-1].content, name="dev_tools")]},
        goto="supervisor"
    )

builder_supervisor = make_supervisor_node(llm, ["dev_tools"])

builder_builder = StateGraph(State)
builder_builder.add_node("supervisor", builder_supervisor)
builder_builder.add_node("dev_tools", dev_tools_node)
builder_builder.add_edge(START, "supervisor")
builder_team_graph = builder_builder.compile()


# === KITCHEN TEAM ===
def recipe_node(state: State) -> Command[Literal["supervisor"]]:
    result = recipe_agent.invoke(state)
    return Command(
        update={"messages": [HumanMessage(content=result["messages"][-1].content, name="recipe")]},
        goto="supervisor"
    )

def team_pm_node(state: State) -> Command[Literal["supervisor"]]:
    result = team_pm_agent.invoke(state)
    return Command(
        update={"messages": [HumanMessage(content=result["messages"][-1].content, name="team_pm")]},
        goto="supervisor"
    )

def dish_ideation_node(state: State) -> Command[Literal["supervisor"]]:
    result = dish_ideation_agent.invoke(state)
    return Command(
        update={"messages": [HumanMessage(content=result["messages"][-1].content, name="dish_ideation")]},
        goto="supervisor"
    )

kitchen_supervisor = make_supervisor_node(llm, ["recipe", "team_pm", "dish_ideation"])

kitchen_builder = StateGraph(State)
kitchen_builder.add_node("supervisor", kitchen_supervisor)
kitchen_builder.add_node("recipe", recipe_node)
kitchen_builder.add_node("team_pm", team_pm_node)
kitchen_builder.add_node("dish_ideation", dish_ideation_node)
kitchen_builder.add_edge(START, "supervisor")
kitchen_team_graph = kitchen_builder.compile()


# === INVENTORY TEAM ===
def stock_node(state: State) -> Command[Literal["supervisor"]]:
    result = stock_agent.invoke(state)
    return Command(
        update={"messages": [HumanMessage(content=result["messages"][-1].content, name="stock")]},
        goto="supervisor"
    )

def suppliers_node(state: State) -> Command[Literal["supervisor"]]:
    result = suppliers_agent.invoke(state)
    return Command(
        update={"messages": [HumanMessage(content=result["messages"][-1].content, name="suppliers")]},
        goto="supervisor"
    )

def analysis_node(state: State) -> Command[Literal["supervisor"]]:
    result = analysis_agent.invoke(state)
    return Command(
        update={"messages": [HumanMessage(content=result["messages"][-1].content, name="analysis")]},
        goto="supervisor"
    )

inventory_supervisor = make_supervisor_node(llm, ["stock", "suppliers", "analysis"])

inventory_builder = StateGraph(State)
inventory_builder.add_node("supervisor", inventory_supervisor)
inventory_builder.add_node("stock", stock_node)
inventory_builder.add_node("suppliers", suppliers_node)
inventory_builder.add_node("analysis", analysis_node)
inventory_builder.add_edge(START, "supervisor")
inventory_team_graph = inventory_builder.compile()


# === SALES TEAM ===
def profit_node(state: State) -> Command[Literal["supervisor"]]:
    result = profit_agent.invoke(state)
    return Command(
        update={"messages": [HumanMessage(content=result["messages"][-1].content, name="profit")]},
        goto="supervisor"
    )

sales_supervisor = make_supervisor_node(llm, ["profit"])

sales_builder = StateGraph(State)
sales_builder.add_node("supervisor", sales_supervisor)
sales_builder.add_node("profit", profit_node)
sales_builder.add_edge(START, "supervisor")
sales_team_graph = sales_builder.compile()


# ========================================================================
# TIER 1: CHEF META-TEAM (combines kitchen, inventory, sales)
# ========================================================================

def call_kitchen_team(state: State) -> Command[Literal["supervisor"]]:
    response = kitchen_team_graph.invoke({"messages": state["messages"]})
    return Command(
        update={"messages": [HumanMessage(content=response["messages"][-1].content, name="kitchen_team")]},
        goto="supervisor"
    )

def call_inventory_team(state: State) -> Command[Literal["supervisor"]]:
    response = inventory_team_graph.invoke({"messages": state["messages"]})
    return Command(
        update={"messages": [HumanMessage(content=response["messages"][-1].content, name="inventory_team")]},
        goto="supervisor"
    )

def call_sales_team(state: State) -> Command[Literal["supervisor"]]:
    response = sales_team_graph.invoke({"messages": state["messages"]})
    return Command(
        update={"messages": [HumanMessage(content=response["messages"][-1].content, name="sales_team")]},
        goto="supervisor"
    )

chef_supervisor = make_supervisor_node(llm, ["kitchen_team", "inventory_team", "sales_team"])

chef_builder = StateGraph(State)
chef_builder.add_node("supervisor", chef_supervisor)
chef_builder.add_node("kitchen_team", call_kitchen_team)
chef_builder.add_node("inventory_team", call_inventory_team)
chef_builder.add_node("sales_team", call_sales_team)
chef_builder.add_edge(START, "supervisor")
chef_team_graph = chef_builder.compile()


# ========================================================================
# TIER 0: ROOT GRAPH (Top-level orchestration)
# ========================================================================

def call_speaker_team(state: State) -> Command[Literal["supervisor"]]:
    response = speaker_team_graph.invoke({"messages": state["messages"]})
    return Command(
        update={"messages": [HumanMessage(content=response["messages"][-1].content, name="speaker_team")]},
        goto="supervisor"
    )

def call_builder_team(state: State) -> Command[Literal["supervisor"]]:
    response = builder_team_graph.invoke({"messages": state["messages"]})
    return Command(
        update={"messages": [HumanMessage(content=response["messages"][-1].content, name="builder_team")]},
        goto="supervisor"
    )

def call_chef_team(state: State) -> Command[Literal["supervisor"]]:
    response = chef_team_graph.invoke({"messages": state["messages"]})
    return Command(
        update={"messages": [HumanMessage(content=response["messages"][-1].content, name="chef_team")]},
        goto="supervisor"
    )

root_supervisor = make_supervisor_node(llm, ["speaker_team", "builder_team", "chef_team"])

root_builder = StateGraph(State)
root_builder.add_node("supervisor", root_supervisor)
root_builder.add_node("speaker_team", call_speaker_team)
root_builder.add_node("builder_team", call_builder_team)
root_builder.add_node("chef_team", call_chef_team)
root_builder.add_edge(START, "supervisor")
root_graph = root_builder.compile()

# Export as 'agent' for LangGraph Cloud
agent = root_graph


# ========================================================================
# TESTING
# ========================================================================

if __name__ == "__main__":
    print("🌳 ROA Agent Garden v3 - Hierarchical Architecture")
    print("=" * 70)
    
    test_queries = [
        "What recipes do we have in Yotam Kitchen?",
        "Check stock levels for tomatoes",
        "Show me a video about pasta recipe",
    ]
    
    for query in test_queries:
        print(f"\n📝 Query: {query}")
        print("-" * 70)
        
        try:
            result = agent.invoke({"messages": [("user", query)]}, {"recursion_limit": 150})
            last_message = result["messages"][-1]
            print(f"💬 Response: {last_message.content}")
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
        
        print("=" * 70)
