"""
ROA Agent Garden v4 - Simplified Hierarchical Multi-Agent System
Based on LangGraph hierarchical teams pattern

Hierarchical Structure:
ROOT AGENT (Conversational - handles all user interaction directly)
├── visualization_agent (visual displays & React Flow)
├── marketing_agent (marketing content)
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

Note: Root agent IS the speaker - no separate voice/speaker team.
"""

import os
from typing import List, Optional, Literal
from typing_extensions import TypedDict
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
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
    routing_recommendations: str  # Conversational agent's routing suggestions
    delegation_path: list  # Track current delegation path: ["supervisor", "chef_team", "recipe"]
    failed_paths: list  # Track failed delegation paths: [["supervisor", "chef_team"], ...]
    attempts_at_level: dict  # Track attempts per supervisor level: {"supervisor": 2, "chef_team->supervisor": 1}
    delegation_depth: int  # Track current delegation depth (0 = root, 1 = chef, 2 = kitchen, etc.)
    max_delegation_depth: int  # Maximum allowed depth (default 4)


# ========== CIRCUIT BREAKER - Simple Loop Prevention ==========
MAX_SAME_WORKER_ATTEMPTS = 2  # Don't retry same worker more than 2x
MAX_TOTAL_ATTEMPTS = 3  # Maximum routing attempts before admitting failure
MAX_DELEGATION_DEPTH = 4  # Maximum hierarchy depth (root=0, chef=1, kitchen=2, worker=3)

def build_tool_table(worker_tools: dict, detail_level: str = "full") -> str:
    """Build tool visibility table with hierarchical abstraction
    
    Args:
        worker_tools: {"worker_name": [list of tool objects] or "description": str}
        detail_level: "full" (direct reports) or "abstract" (grandchildren teams)
        
    Returns:
        Formatted table - detailed for direct reports, abstract for distant teams
    """
    table = "\n" + "="*100 + "\n"
    table += "AVAILABLE CAPABILITIES (by Worker):\n"
    table += "="*100 + "\n\n"
    
    for worker_name, worker_info in worker_tools.items():
        table += f"📦 {worker_name.upper()}:\n"
        table += "-" * 100 + "\n"
        
        # Check if this is abstract (team description) or detailed (tool list)
        if isinstance(worker_info, str):
            # Abstract description for distant teams
            table += f"  {worker_info}\n\n"
        elif isinstance(worker_info, list):
            # Detailed tool list for direct reports
            tools = worker_info
            
            if not tools:
                table += "  (No direct tools - delegates to subagents)\n\n"
                continue
                
            for tool in tools:
                tool_name = tool.name
                tool_desc = tool.description.split("\n")[0] if tool.description else "No description"
                
                table += f"  🔧 {tool_name}\n"
                table += f"     Description: {tool_desc}\n"
                
                # Extract args from tool schema if available
                if hasattr(tool, 'args_schema') and tool.args_schema:
                    table += f"     Args: {list(tool.args_schema.__fields__.keys())}\n"
                
                table += "\n"
        
    table += "="*100 + "\n"
    return table

def check_circuit_breaker(state: State, worker_name: str) -> tuple[bool, str]:
    """Simple circuit breaker - prevent obvious loops and unbounded delegation
    
    Returns:
        (can_delegate: bool, reason: str)
    """
    attempts_at_level = state.get("attempts_at_level", {})
    
    # Check delegation depth (prevent infinite hierarchy)
    current_depth = state.get("delegation_depth", 0)
    max_depth = state.get("max_delegation_depth", MAX_DELEGATION_DEPTH)
    if current_depth >= max_depth:
        return (False, f"Circuit breaker: Max delegation depth ({max_depth}) reached. Escalating to human.")
    
    # Check total attempts (prevent exhaustive exploration)
    total_attempts = sum(attempts_at_level.values())
    if total_attempts >= MAX_TOTAL_ATTEMPTS:
        return (False, f"Circuit breaker: {total_attempts} routing attempts made. With full tool visibility, supervisor should know upfront if request is possible.")
    
    # Check same worker attempts (prevent retrying same failed worker)
    worker_attempts = attempts_at_level.get(worker_name, 0)
    if worker_attempts >= MAX_SAME_WORKER_ATTEMPTS:
        return (False, f"Circuit breaker: Already tried {worker_name} {worker_attempts} times. If worker can't do it, they can't do it.")
    
    return (True, "")

def record_delegation_attempt(state: State, worker_name: str) -> dict:
    """Record that we're attempting to delegate to worker"""
    current_path = state.get("delegation_path", []).copy()
    new_path = current_path + [worker_name]
    
    attempts_at_level = state.get("attempts_at_level", {}).copy()
    attempts_at_level[worker_name] = attempts_at_level.get(worker_name, 0) + 1
    
    # Increment delegation depth
    current_depth = state.get("delegation_depth", 0)
    new_depth = len(new_path)  # Depth = length of delegation path
    
    total_attempts = sum(attempts_at_level.values())
    print(f"📍 DELEGATION #{total_attempts} (depth={new_depth}): {' -> '.join(new_path)}")
    
    return {
        "delegation_path": new_path,
        "attempts_at_level": attempts_at_level,
        "delegation_depth": new_depth,
        "max_delegation_depth": state.get("max_delegation_depth", MAX_DELEGATION_DEPTH)
    }

def record_delegation_failure(state: State, worker_name: str, reason: str) -> dict:
    """Record a failed delegation
    
    Failures are detected when:
    - Worker reports error/limitation ("cannot", "unable to", etc.)
    - Tool call fails  
    - Worker returns without completing task
    """
    failed_paths = state.get("failed_paths", []).copy()
    failed_paths.append(worker_name)
    
    print(f"❌ WORKER FAILED: {worker_name}")
    print(f"   Reason: {reason[:100]}...")
    print(f"   Failed workers so far: {failed_paths}")
    
    return {
        "failed_paths": failed_paths
    }

def evaluate_worker_output(task: str, output: str, llm) -> dict:
    """Judge Agent - Evaluates quality of worker outputs
    
    Args:
        task: Original user task/query
        output: Worker's response
        llm: Language model for evaluation
        
    Returns:
        {
            "score": int (1-10),
            "is_sufficient": bool,
            "critique": str,
            "needs_retry": bool
        }
    """
    from pydantic import BaseModel, Field
    
    class Evaluation(BaseModel):
        score: int = Field(description="Quality score from 1-10")
        is_sufficient: bool = Field(description="True if output fully answers the task")
        critique: str = Field(description="Specific feedback on what's missing or wrong")
        needs_retry: bool = Field(description="True if worker should retry with feedback")
    
    evaluation_prompt = f"""You are a quality judge for a multi-agent system.
    
USER TASK: {task}
WORKER OUTPUT: {output}

Evaluate the worker's output on:
1. **Accuracy** - Is the information correct?
2. **Completeness** - Does it fully answer the user's question?
3. **Clarity** - Is it well-formatted and easy to understand?

Rate 1-10 (10 = perfect, 1 = completely wrong).

Scoring guidelines:
- 9-10: Excellent, complete answer
- 7-8: Good, minor improvements possible
- 5-6: Acceptable but incomplete
- 3-4: Poor, significant issues
- 1-2: Wrong or useless

Mark is_sufficient=True if score >= 7.
Mark needs_retry=True if score < 7 AND the issue is fixable.
Provide specific critique for improvement.
"""
    
    try:
        result = llm.with_structured_output(Evaluation).invoke(evaluation_prompt)
        return {
            "score": result.score,
            "is_sufficient": result.is_sufficient,
            "critique": result.critique,
            "needs_retry": result.needs_retry
        }
    except Exception as e:
        # If evaluation fails, assume output is acceptable
        print(f"⚠️  Evaluation failed: {e}, accepting output")
        return {
            "score": 7,
            "is_sufficient": True,
            "critique": "Evaluation unavailable",
            "needs_retry": False
        }

def record_delegation_success(state: State) -> dict:
    """Record successful delegation - reset counters for this branch"""
    current_path = state.get("delegation_path", [])
    print(f"✅ PATH SUCCESS: {' -> '.join(current_path)}")
    
    # Reset delegation path (task complete)
    return {
        "delegation_path": [],
        "attempts_at_level": {}  # Reset attempts
    }


# ========== SUPERVISOR HELPER ==========
def make_supervisor_node(llm, members: list[str], worker_tools: dict = None):
    """Create a supervisor node that routes to team members
    
    Args:
        llm: Language model for routing decisions
        members: List of worker names
        worker_tools: Dict of {worker_name: [tool objects]} for full visibility
    """
    options = ["FINISH"] + members
    worker_tools = worker_tools or {}
    
    # Build tool visibility table
    tool_table = build_tool_table(worker_tools) if worker_tools else ""
    
    # Build descriptions for each worker based on their name
    worker_descriptions = {
        # Direct workers (attached to root)
        "visualization": "Creates visual displays. TOOLS: display_recipes, display_multiplication, display_prediction_graph, display_inventory_alert, display_team_assignment. Use when user wants to SEE data graphically.",
        "marketing": "Generates marketing content. TOOLS: create_marketing_content. Use for promotional/marketing requests only.",
        # Kitchen team agents  
        "recipe": "Searches/retrieves recipes from Neo4j database. TOOLS: search_recipes, get_recipe_details. Can find recipes by name or kitchen.",
        "team_pm": "Manages kitchen team. TOOLS: get_team_members, assign_task",
        "dish_ideation": "Brainstorms new dishes. TOOLS: suggest_dishes (based on ingredients)",
        # Inventory team agents
        "stock": "Checks inventory levels. TOOLS: check_stock (by item or full inventory)",
        "suppliers": "Manages suppliers. TOOLS: list_suppliers",
        "analysis": "Forecasts demand. TOOLS: forecast_demand (predicts inventory needs)",
        # Sales team agents
        "profit": "Analyzes costs/profits. TOOLS: calculate_cost (recipe cost per serving)",
        # Top-level teams
        "builder_team": "Developer tools team. Subagents: dev_tools (code generation). Use only for development/debugging.",
        "chef_team": "Complete kitchen operations. Subagents: kitchen_team (recipes/team/dishes), inventory_team (stock/suppliers/forecasts), sales_team (cost/profit). Use for ALL food/cooking/kitchen questions.",
        "kitchen_team": "Recipe & team management. Subagents: recipe (search/details from DB), team_pm (members/tasks), dish_ideation (suggest dishes). Has access to Neo4j recipe database.",
        "inventory_team": "Stock management. Subagents: stock (check levels), suppliers (list), analysis (forecast demand).",
        "sales_team": "Financial analysis. Subagents: profit (calculate recipe costs)."
    }
    
    worker_info = "\n".join([f"- {name}: {worker_descriptions.get(name, 'Specialized worker')}" 
                             for name in members])
    
    # Build routing examples based on available workers
    routing_examples = []
    if "visualization" in members:
        routing_examples.extend([
            '"show me pasta recipes visually" → visualization (has display_recipes tool)',
            '"visualize the team assignments" → visualization (has display_team_assignment)',
            '"chart the inventory forecast" → visualization (has display_prediction_graph)'
        ])
    if "marketing" in members:
        routing_examples.append('"create marketing copy for our new dish" → marketing (promotional content)')
    if "chef_team" in members:
        routing_examples.extend([
            '"get Arroz Sushi recipe" → chef_team (recipe database access)',
            '"what ingredients do I need" → chef_team (recipe/inventory info)',
            '"check stock levels" → chef_team (inventory management)'
        ])
    if "recipe" in members:
        routing_examples.extend([
            '"find sushi recipes" → recipe (has search_recipes tool)',
            '"get details for Gazpacho" → recipe (has get_recipe_details tool)'
        ])
    if "stock" in members:
        routing_examples.append('"what\'s in the pantry" → stock (has check_stock tool)')
    
    examples_text = "\n".join([f"  {ex}" for ex in routing_examples]) if routing_examples else "  (no examples for this team)"
    
    system_prompt = f"""You are a routing supervisor for a restaurant operations assistant.

YOUR ROLE: Make final routing decisions based on:
1. User's request
2. Conversation history
3. Routing recommendations from the conversational agent (if provided)

AVAILABLE WORKERS:
{worker_info}

ROUTING EXAMPLES:
{examples_text}

ROUTING RECOMMENDATIONS:
The conversational agent may provide routing suggestions in the state. Consider these as helpful guidance, but make your own decision based on:
- User's actual needs
- Worker capabilities and tools
- Current conversation context
- Your judgment as supervisor

WHEN TO FINISH (respond directly, no delegation):
- Greetings: "hello", "hi", "good morning"
- Acknowledgments: "thanks", "got it", "okay"
- General questions: "what can you do?", "how are you?"
- Simple confirmations: "yes", "no", "sounds good"
→ For these, respond with FINISH immediately so root can answer conversationally

WHEN TO DELEGATE (route to worker):
- Recipe requests → chef_team
- Inventory checks → chef_team
- Visual displays → visualization
- Marketing content → marketing
- Development tasks → builder_team

ROUTING RULES (CRITICAL):
1. Check the LAST message - if it has a 'name' field matching a worker, that worker JUST responded
2. NEVER route back to a worker that just provided a response
3. Each worker should be called ONCE maximum per user request
4. For conversational inputs, DEFAULT TO FINISH (let root respond naturally)
5. Only delegate when user needs specific expertise/tools

⚠️ CRITICAL - TOOL VISIBILITY:
You have COMPLETE VISIBILITY of all tools available to your workers (see table below).
Use this to make INFORMED routing decisions UPFRONT.

With tool visibility, you should:
1. Match user request to available tools
2. Route to worker who HAS the needed tool
3. If NO worker has needed tool → respond FINISH immediately (don't waste attempts)
4. Don't blindly explore - you know what each worker can do!

⚠️ CIRCUIT BREAKER (Simple Loop Prevention):
- Max {MAX_SAME_WORKER_ATTEMPTS} attempts per worker (don't retry if they already failed)
- Max {MAX_TOTAL_ATTEMPTS} total routing attempts (with visibility, should route correctly first try)
- Circuit breaker is SAFETY NET for bugs, not exploration strategy

TERMINATE (respond with FINISH) when:
a. User input is conversational (greeting, thanks, simple question)
b. A worker just provided a complete answer
c. The user's request is fully satisfied
d. NO worker has tools to handle request (check tool table!)
e. Circuit breaker trips (routing bug - shouldn't happen with tool visibility)

Your available workers: {members}
{tool_table}
Respond ONLY with the worker name OR 'FINISH'."""
    
    class Router(TypedDict):
        """Worker to route to next"""
        next: Literal[tuple(options)]
    
    def supervisor_node(state: State) -> Command[Literal[tuple(members + ["__end__"])]]:
        # Check if last message indicates error/limitation from a worker
        last_message = state["messages"][-1] if state["messages"] else None
        if last_message and hasattr(last_message, 'name') and hasattr(last_message, 'content'):
            worker_name = last_message.name if hasattr(last_message, 'name') else "unknown"
            content_lower = last_message.content.lower()
            error_indicators = ["cannot", "can't", "unable to", "don't have", "do not have", "no ability", "not able to"]
            
            if any(indicator in content_lower for indicator in error_indicators):
                # Worker reported limitation - record failure
                failure_reason = f"Worker reported limitation: {last_message.content[:200]}"
                record_delegation_failure(state, worker_name, failure_reason)
                # Supervisor will see tool table and decide if alternative exists
        
        # Include routing recommendations from conversational agent if available
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add routing recommendations as context if provided
        if state.get("routing_recommendations"):
            messages.append({
                "role": "system", 
                "content": f"ROUTING RECOMMENDATIONS FROM CONVERSATIONAL AGENT:\n{state['routing_recommendations']}\n\nConsider these suggestions but make your own final decision."
            })
        
        messages.extend(state["messages"])
        response = llm.with_structured_output(Router).invoke(messages)
        goto = response["next"]
        
        if goto == "FINISH":
            # Task complete - record success
            success_data = record_delegation_success(state)
            success_data["next"] = goto
            return Command(goto=END, update=success_data)
        
        # CIRCUIT BREAKER: Simple loop prevention
        can_delegate, breaker_reason = check_circuit_breaker(state, goto)
        
        if not can_delegate:
            print(f"🔴 {breaker_reason}")
            circuit_breaker_msg = HumanMessage(
                content=f"⚠️ Circuit breaker triggered: {breaker_reason}\n\nI cannot complete this request with available tools. With full tool visibility, I should have routed correctly on first attempt. This indicates either: (1) No tool exists for this request, or (2) A routing bug.",
                name="system"
            )
            return Command(
                goto=END,
                update={
                    "next": "FINISH",
                    "messages": [circuit_breaker_msg]
                }
            )
        
        # Record delegation attempt (add to path)
        attempt_data = record_delegation_attempt(state, goto)
        attempt_data["next"] = goto
        
        return Command(goto=goto, update=attempt_data)
    
    return supervisor_node


# ========================================================================
# TIER 3: TOOLS (organized by domain)
# ========================================================================

# --- Visualization Tools ---
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

# --- Recipe Tools (REAL - from v2) with Optional Fuzzy Matching + Retry Logic ---
@tool
@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=2, max=5),
    retry=retry_if_exception_type((ConnectionError, TimeoutError))
)
def search_recipes(kitchen_name: Optional[str] = None, recipe_name: Optional[str] = None) -> str:
    """Search for recipes with optional fuzzy matching support + automatic retry on connection errors"""
    try:
        if recipe_name:
            # Try fuzzy matching IF rapidfuzz is available
            try:
                from rapidfuzz import fuzz, process
                
                # Get all recipes to fuzzy match against
                if kitchen_name:
                    query = "MATCH (k:Kitchen {name: $kitchen_name})-[:HAS_RECIPE]->(r:Recipe) RETURN k.name as kitchen, r.name as recipe"
                    results = run_query(query, {"kitchen_name": kitchen_name})
                else:
                    query = "MATCH (k:Kitchen)-[:HAS_RECIPE]->(r:Recipe) RETURN k.name as kitchen, r.name as recipe LIMIT 100"
                    results = run_query(query)
                
                if not results:
                    return "No recipes found in database"
                
                # Extract recipe names for fuzzy matching
                recipe_names = [r['recipe'] for r in results]
                
                # Find best matches (threshold 70% similarity)
                matches = process.extract(recipe_name, recipe_names, scorer=fuzz.ratio, limit=5)
                good_matches = [(name, score) for name, score, _ in matches if score >= 70]
                
                if good_matches:
                    # Return matching recipes with confidence scores
                    match_info = "\n".join([f"  - {name} (match: {score}%)" for name, score in good_matches])
                    return f"Found {len(good_matches)} matching recipes:\n{match_info}"
                else:
                    return f"No recipes found matching '{recipe_name}'. Try: {', '.join(recipe_names[:5])}"
                    
            except ImportError:
                # rapidfuzz not available - try exact match only
                if kitchen_name:
                    query = "MATCH (k:Kitchen {name: $kitchen_name})-[:HAS_RECIPE]->(r:Recipe) WHERE r.name CONTAINS $recipe_name RETURN k.name as kitchen, r.name as recipe"
                    results = run_query(query, {"kitchen_name": kitchen_name, "recipe_name": recipe_name})
                else:
                    query = "MATCH (k:Kitchen)-[:HAS_RECIPE]->(r:Recipe) WHERE r.name CONTAINS $recipe_name RETURN k.name as kitchen, r.name as recipe LIMIT 20"
                    results = run_query(query, {"recipe_name": recipe_name})
                
                return f"Found {len(results)} recipes: {results}" if results else f"No recipes matching '{recipe_name}' found. Fuzzy matching unavailable - use exact spelling."
        
        elif kitchen_name:
            query = "MATCH (k:Kitchen {name: $kitchen_name})-[:HAS_RECIPE]->(r:Recipe) RETURN k.name as kitchen, r.name as recipe"
            results = run_query(query, {"kitchen_name": kitchen_name})
        else:
            query = "MATCH (k:Kitchen)-[:HAS_RECIPE]->(r:Recipe) RETURN k.name as kitchen, r.name as recipe LIMIT 20"
            results = run_query(query)
        
        return f"Found {len(results)} recipes: {results}" if results else "No recipes found"
    except Exception as e:
        error_msg = f"RecipeSearchError: Failed searching recipes (kitchen={kitchen_name}, recipe={recipe_name}). Error: {type(e).__name__}: {str(e)}"
        return error_msg  # Return error as string so agent can see it, but it will show in traces

@tool
@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=2, max=5),
    retry=retry_if_exception_type((ConnectionError, TimeoutError))
)
def get_recipe_details(recipe_name: str, kitchen_name: Optional[str] = None) -> str:
    """Get recipe details with optional fuzzy matching fallback + automatic retry on connection errors"""
    try:
        # Try exact match first
        query = """
        MATCH (k:Kitchen)-[:HAS_RECIPE]->(r:Recipe {name: $recipe_name})
        OPTIONAL MATCH (r)-[u:USES]->(c:Component)
        RETURN r.name, r.directions, collect({name: c.name, amount: u.amount, unit: u.unit}) as ingredients
        LIMIT 1
        """
        results = run_query(query, {"recipe_name": recipe_name})
        
        if results:
            return f"Recipe: {results[0]}"
        
        # Exact match failed - try fuzzy matching IF rapidfuzz is available
        try:
            from rapidfuzz import fuzz, process
            
            # Get all recipe names
            all_recipes_query = "MATCH (r:Recipe) RETURN r.name as name LIMIT 100"
            all_recipes = run_query(all_recipes_query)
            
            if not all_recipes:
                return "No recipes found in database"
            
            recipe_names = [r['name'] for r in all_recipes]
            
            # Find best match
            best_match = process.extractOne(recipe_name, recipe_names, scorer=fuzz.ratio)
            
            if best_match and best_match[1] >= 75:  # 75% similarity threshold
                matched_name = best_match[0]
                # Get details for the matched recipe
                results = run_query(query, {"recipe_name": matched_name})
                if results:
                    return f"Found similar recipe '{matched_name}' (you searched for '{recipe_name}'):\n{results[0]}"
            
            # Still no match - suggest alternatives
            suggestions = process.extract(recipe_name, recipe_names, scorer=fuzz.ratio, limit=3)
            suggestion_text = ", ".join([name for name, score, _ in suggestions])
            return f"Recipe '{recipe_name}' not found. Did you mean: {suggestion_text}?"
            
        except ImportError:
            # rapidfuzz not available - just return "not found" without fuzzy matching
            return f"Recipe '{recipe_name}' not found. Please check the exact spelling (case-sensitive). Fuzzy matching unavailable."
        
    except Exception as e:
        error_msg = f"RecipeDetailsError: Failed getting details for '{recipe_name}'. Error: {type(e).__name__}: {str(e)}"
        return error_msg  # Return error as string so agent can see it, but it will show in traces

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

# Direct visualization and marketing agents (attached to root)
visualization_agent = create_react_agent(
    llm, 
    [display_recipes, display_multiplication, display_prediction_graph, display_inventory_alert, display_team_assignment],
    prompt="""You are a visualization specialist for kitchen operations.

ROLE: Create visual displays when users need to SEE data graphically.
INPUT: Requests for charts, graphs, visual recipe cards, team boards
OUTPUT: Text response with embedded VISUALIZATION JSON

RULES:
1. ONLY create visualizations when explicitly requested or clearly beneficial
2. Return descriptive text PLUS embedded JSON for frontend rendering
3. Available displays: recipe cards, inventory alerts, team assignments, prediction graphs
4. If user just wants information (not visualization), let supervisor route elsewhere"""
)

marketing_agent = create_react_agent(
    llm, 
    [create_marketing_content],
    prompt="""You are a marketing content creator for culinary products.

ROLE: Generate marketing copy and promotional content.
INPUT: Product names, dishes, or promotional requests
OUTPUT: Engaging marketing text

RULES:
1. ONLY handle marketing/promotional content requests
2. Keep copy professional and suitable for food industry
3. If request isn't about marketing, return error so supervisor can re-route"""
)

# Builder team workers
dev_tools_agent = create_react_agent(
    llm, 
    [generate_tool_code],
    prompt="""You are a developer tool assistant.

ROLE: Generate Python code for tools and scripts.
INPUT: Tool names, descriptions, or code requests
OUTPUT: Python code snippets

RULES:
1. ONLY handle code generation requests
2. Keep code concise, readable, and well-documented
3. If request isn't about code, return error so supervisor can re-route"""
)

# Kitchen team workers
recipe_agent = create_react_agent(
    llm, 
    [search_recipes, get_recipe_details],
    prompt="""You are a recipe database specialist with access to Neo4j database.

ROLE: Search and retrieve recipe information from Neo4j.
INPUT: Recipe names (may contain typos/numbers), ingredient lists, dietary requirements
OUTPUT: Recipe names with descriptions, detailed recipe info

AVAILABLE TOOLS:
- search_recipes(kitchen_name?, recipe_name?) - Find recipes by name or list all in kitchen
- get_recipe_details(recipe_name, kitchen_name?) - Get full recipe (ingredients, directions, etc.)

DATABASE INFO:
- Contains recipes like: "Arroz Sushi", "Gazpacho", "Salmón Confitado", "Tartar de Salmón con Arroz de Sushi"
- Recipe names are case-sensitive and must match exactly
- Common variations: "Arroz" (not "arruz"), "Salmón" (not "salmon")

HANDLING USER INPUT:
1. Extract recipe name from user query (ignore numbers like "3 arruz sushi" → "arruz sushi")
2. Fix common typos before searching (arruz→Arroz, salmon→Salmón, gazpaco→Gazpacho)
3. Try exact match first, then search all recipes and find closest match
4. If not found, suggest similar recipes from database

RULES:
1. ONLY handle recipe operations - NOT inventory, team, or sales
2. NEVER make up recipes - only return actual database results
3. If no match, search ALL recipes and suggest closest ones
4. For ambiguous requests, ask ONE clarifying question"""
)

team_pm_agent = create_react_agent(
    llm, 
    [get_team_members, assign_task],
    prompt="""You are a team project manager.

ROLE: Manage team members, tasks, and assignments.
INPUT: Team member names, task descriptions, assignment requests
OUTPUT: Team member lists, task assignments, confirmation of changes

AVAILABLE OPERATIONS:
- get_team_members: List team members
- assign_task: Assign task to team member

RULES:
1. ONLY handle team management operations
2. Keep assignments clear and concise
3. If request isn't about team management, return error so supervisor can re-route"""
)

dish_ideation_agent = create_react_agent(
    llm, 
    [suggest_dishes],
    prompt="""You are a dish ideation specialist.

ROLE: Suggest dish ideas based on ingredients.
INPUT: Ingredient lists
OUTPUT: Dish ideas

RULES:
1. ONLY handle dish ideation requests
2. Keep suggestions creative and relevant
3. If request isn't about dish ideation, return error so supervisor can re-route"""
)

# Inventory team workers
stock_agent = create_react_agent(
    llm, 
    [check_stock],
    prompt="""You are an inventory management specialist.

ROLE: Check stock levels and manage inventory.
INPUT: Item names, stock requests
OUTPUT: Stock levels, confirmation of changes

AVAILABLE OPERATIONS:
- check_stock: Check stock level of item

RULES:
1. ONLY handle inventory management operations
2. Keep stock levels accurate and up-to-date
3. If request isn't about inventory, return error so supervisor can re-route"""
)

suppliers_agent = create_react_agent(
    llm, 
    [list_suppliers],
    prompt="""You are a supplier management specialist.

ROLE: Manage suppliers and their information.
INPUT: Supplier names, requests for supplier lists
OUTPUT: Supplier lists

AVAILABLE OPERATIONS:
- list_suppliers: List suppliers

RULES:
1. ONLY handle supplier management operations
2. Keep supplier information accurate and up-to-date
3. If request isn't about suppliers, return error so supervisor can re-route"""
)

analysis_agent = create_react_agent(
    llm, 
    [forecast_demand],
    prompt="""You are a demand forecasting specialist.

ROLE: Forecast demand for items.
INPUT: Item names, demand requests
OUTPUT: Demand forecasts

AVAILABLE OPERATIONS:
- forecast_demand: Forecast demand for item

RULES:
1. ONLY handle demand forecasting operations
2. Keep forecasts accurate and up-to-date
3. If request isn't about demand forecasting, return error so supervisor can re-route"""
)

# Sales team workers
profit_agent = create_react_agent(
    llm,
    [calculate_cost],
    prompt="""You are a profitability analyst.

ROLE: Calculate costs and analyze profit margins.
INPUT: Recipe names, cost calculation requests
OUTPUT: Cost breakdowns, profit analysis

AVAILABLE OPERATIONS:
- calculate_cost: Calculate cost per serving for recipes

RULES:
1. ONLY handle cost/profit analysis operations
2. Return accurate cost information
3. If request isn't about costs/profits, return error so supervisor can re-route"""
)


# ========================================================================
# TIER 1.5: TEAM GRAPHS (Subgraphs with their own supervisors)
# ========================================================================

# === DIRECT WORKERS (attached to root) ===
def visualization_node(state: State) -> Command[Literal["supervisor"]]:
    result = visualization_agent.invoke(state)
    return Command(
        update={"messages": [HumanMessage(content=result["messages"][-1].content, name="visualization")]},
        goto="supervisor"
    )

def marketing_node(state: State) -> Command[Literal["supervisor"]]:
    result = marketing_agent.invoke(state)
    return Command(
        update={"messages": [HumanMessage(content=result["messages"][-1].content, name="marketing")]},
        goto="supervisor"
    )


# === BUILDER TEAM ===
def dev_tools_node(state: State) -> Command[Literal["supervisor"]]:
    result = dev_tools_agent.invoke(state)
    return Command(
        update={"messages": [HumanMessage(content=result["messages"][-1].content, name="dev_tools")]},
        goto="supervisor"
    )

builder_supervisor = make_supervisor_node(llm, ["dev_tools"], worker_tools={
    "dev_tools": [generate_tool_code]
})

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

kitchen_supervisor = make_supervisor_node(llm, ["recipe", "team_pm", "dish_ideation"], worker_tools={
    "recipe": [search_recipes, get_recipe_details],
    "team_pm": [get_team_members, assign_task],
    "dish_ideation": [suggest_dishes]
})

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

inventory_supervisor = make_supervisor_node(llm, ["stock", "suppliers", "analysis"], worker_tools={
    "stock": [check_stock],
    "suppliers": [list_suppliers],
    "analysis": [forecast_demand]
})

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

sales_supervisor = make_supervisor_node(llm, ["profit"], worker_tools={
    "profit": [calculate_cost]
})

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

# Chef supervisor sees ABSTRACT descriptions (not granular tools)
# Direct reports are teams, so show capabilities not individual tools
chef_supervisor = make_supervisor_node(llm, ["kitchen_team", "inventory_team", "sales_team"], worker_tools={
    "kitchen_team": "Manages recipes, team assignments, and dish planning. Handles: searching recipes, getting recipe details, managing team members, and suggesting new dishes.",
    "inventory_team": "Tracks inventory and supplier relationships. Handles: checking stock levels, listing suppliers, and forecasting demand.",
    "sales_team": "Analyzes costs and profitability. Handles: calculating recipe costs and profit margins."
})

chef_builder = StateGraph(State)
chef_builder.add_node("supervisor", chef_supervisor)
chef_builder.add_node("kitchen_team", call_kitchen_team)
chef_builder.add_node("inventory_team", call_inventory_team)
chef_builder.add_node("sales_team", call_sales_team)
chef_builder.add_edge(START, "supervisor")
chef_team_graph = chef_builder.compile()


# ========================================================================
# TIER 0: ROOT GRAPH (Conversational agent with direct access to workers)
# ========================================================================
# Root agent handles all conversation directly - no separate speaker layer
# Flow: START → conversational_responder → supervisor (if needed) → workers → END

# Create a conversational agent for root-level responses AND routing recommendations
conversational_agent = create_react_agent(
    llm,
    [],  # No tools - pure conversation
    prompt="""You are ROA, a friendly and professional restaurant operations assistant with full conversation awareness.

ROLE: Handle direct conversation AND provide routing recommendations for complex requests.
STYLE: Natural, helpful, concise, professional

You can:
- Answer greetings warmly
- Explain your capabilities
- Provide general guidance
- Acknowledge user feedback
- Respond to simple questions

For complex requests, you understand the FULL conversation context and can recommend sophisticated routing strategies.

RULES:
1. Be warm and professional
2. Keep responses concise (2-3 sentences max for simple interactions)
3. Don't make up data - if you need specific info, say so
4. For complex requests, confirm you'll help and provide routing guidance"""
)

# Create a routing planner that analyzes requests and suggests routing
routing_planner = create_react_agent(
    llm,
    [],  # No tools - just analysis
    prompt="""You are a routing planner for a restaurant operations assistant.

AVAILABLE WORKERS:
- visualization: Creates visual displays (recipes, graphs, team assignments, forecasts)
- marketing: Generates promotional content
- chef_team: Handles ALL kitchen operations (recipes, inventory, team, sales)
  └─ Sub-teams: kitchen_team (recipes/team/dishes), inventory_team (stock/suppliers/forecasts), sales_team (cost analysis)
- builder_team: Development tools (code generation)

YOUR ROLE: Analyze user requests in context of the full conversation and suggest routing strategies.

Consider:
1. What is the user actually asking for?
2. What data/tools are needed?
3. Could this benefit from multiple agents? (e.g., get recipe + visualize it)
4. What's the logical sequence if multiple agents needed?

OUTPUT FORMAT:
Provide clear, concise routing recommendations:
- Single agent: "Route to [agent_name] because [reason]"
- Multiple agents: "Suggested sequence: 1) [agent] for [task], 2) [agent] for [task]"
- Uncertain: "Recommend [agent] but may need [alternative] if [condition]"

Examples:
- "get Arroz Sushi recipe" → "Route to chef_team (kitchen_team → recipe) to search Neo4j database"
- "show me pasta recipes visually" → "Sequence: 1) chef_team (recipes) to get data, 2) visualization to display"
- "what's in stock and create a forecast chart" → "Sequence: 1) chef_team (inventory) for stock data, 2) chef_team (analysis) for forecast, 3) visualization for chart"
"""
)

def conversational_responder_node(state: State) -> Command[Literal["supervisor", "__end__"]]:
    """Handle initial conversation and decide if delegation is needed
    
    For simple conversation: Respond directly and end
    For complex requests: Generate routing recommendations and pass to supervisor
    """
    last_message = state["messages"][-1]
    
    # Simple conversational inputs - respond directly and end
    conversational_keywords = ["hello", "hi", "hey", "thanks", "thank you", "ok", "okay", "got it"]
    user_message = last_message.content.lower() if hasattr(last_message, 'content') else str(last_message[1]).lower()
    
    # Check if this is a simple conversational input
    is_simple_conversation = any(keyword in user_message for keyword in conversational_keywords) and len(user_message.split()) <= 5
    
    if is_simple_conversation:
        # Respond conversationally and end
        result = conversational_agent.invoke(state)
        return Command(
            update={"messages": [HumanMessage(content=result["messages"][-1].content, name="assistant")]},
            goto=END
        )
    else:
        # Complex request - generate routing recommendations
        # The routing planner has full conversation context and can suggest sophisticated strategies
        routing_result = routing_planner.invoke(state)
        routing_recommendations = routing_result["messages"][-1].content
        
        # Pass recommendations to supervisor for final decision
        return Command(
            update={"routing_recommendations": routing_recommendations},
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

# Root supervisor sees VERY ABSTRACT descriptions (2+ layers from tools)
# Only knows general purpose of each top-level team
root_supervisor = make_supervisor_node(llm, ["visualization", "marketing", "builder_team", "chef_team"], worker_tools={
    "visualization": [display_recipes, display_multiplication, display_prediction_graph, display_inventory_alert, display_team_assignment],  # Direct report - keep detailed
    "marketing": [create_marketing_content],  # Direct report - keep detailed
    "builder_team": [generate_tool_code],  # Direct report - keep detailed
    "chef_team": "Handles ALL kitchen operations: recipes, inventory, team management, cost analysis, and sales planning. Delegates to specialized subteams."  # Meta-team - abstract!
})

root_builder = StateGraph(State)
root_builder.add_node("conversational_responder", conversational_responder_node)
root_builder.add_node("supervisor", root_supervisor)
root_builder.add_node("visualization", visualization_node)
root_builder.add_node("marketing", marketing_node)
root_builder.add_node("builder_team", call_builder_team)
root_builder.add_node("chef_team", call_chef_team)
root_builder.add_edge(START, "conversational_responder")  # Start with conversation
root_graph = root_builder.compile()

# Export as 'agent' for LangGraph Cloud
agent = root_graph


# ========================================================================
# TESTING
# ========================================================================

if __name__ == "__main__":
    print("🌳 ROA Agent Garden v4 - Simplified Architecture")
    print("=" * 70)
    
    test_queries = [
        "What recipes do we have in Yotam Kitchen?",
        "Check stock levels for tomatoes",
        "Show me a visualization of pasta recipes",
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
