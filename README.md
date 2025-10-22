# 🤖 Agent Microservice

LangGraph AI agent for restaurant operations.

## Tech Stack

- **Framework**: LangGraph
- **LLM**: Google Gemini 2.5 Flash
- **Language**: Python 3.11+
- **Deployment**: LangGraph Cloud

## Files

- `roa_agent.py` - Main agent code
- `langgraph.json` - LangGraph deployment config
- `requirements.txt` - Python dependencies
- `.env.example` - Environment variable template

## Environment Variables

```bash
GOOGLE_API_KEY=    # Gemini AI API key
SUPABASE_URL=      # Supabase project URL
SUPABASE_KEY=      # Supabase anon key
```

## Agent Capabilities

### Database Tools (Read)
- `get_all_recipes()` - List all recipes
- `get_recipe_details(name)` - Get recipe with ingredients
- `get_all_ingredients()` - List all components
- `get_all_kitchens()` - List all kitchens
- `get_all_users()` - List all users

### Database Tools (Write)
- `add_recipe(name, directions)` - Add new recipe
- `add_component(name, type)` - Add new ingredient
- `update_recipe_directions(name, directions)` - Update recipe

### Utility Tools
- `calculate(expression)` - Math operations (scaling, costs, etc.)

## System Prompt

The agent is ROA (Restaurant Operations Assistant), designed to:
- Help with recipe management
- Assist with kitchen operations
- Perform calculations
- Query and update database
- Maintain professional, concise communication

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env with your values

# Run LangGraph dev server
langgraph dev
```

Server runs on http://localhost:8123

## Deploy to LangGraph Cloud

```bash
# Install LangGraph CLI
pip install langgraph-cli

# Deploy
langgraph deploy

# Or push to GitHub and deploy via LangGraph UI
```

## Architecture

```
Input: {"messages": [{"role": "user", "content": "..."}]}
  ↓
System Prompt (ROA identity)
  ↓
Gemini 2.5 Flash (decides which tool to use)
  ↓
Tool Execution (database query or calculation)
  ↓
Gemini 2.5 Flash (formats response)
  ↓
Output: {"messages": [..., {"role": "assistant", "content": "..."}]}
```

## Graph Structure

```
START → assistant → tools → assistant → END
         ↑______________|
```

- **assistant**: Gemini LLM with tools
- **tools**: Execute selected tool
- **Conditional edge**: Routes to tools if LLM calls a tool, otherwise ends

## Memory

- **Thread-based**: Each user gets a separate conversation thread
- **Managed by LangGraph Cloud**: Automatic checkpoint storage
- **Stateless agent code**: No explicit checkpointer in code

## Dependencies

- `langgraph` - Agent framework
- `langchain-core` - Core LangChain components
- `langchain-google-genai` - Gemini integration
- `supabase` - Database client
