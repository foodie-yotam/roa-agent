# ROA Agent v2 - Neo4j Deployment

## ✅ Ready to Deploy

### Changes Made:
1. **New Agent**: `roa_agent_v2.py` (Neo4j-based)
2. **Config Updated**: `langgraph.json` points to v2
3. **Old Agent**: `roa_agent.py` (Supabase - preserved)

### 5 Core Tools (Optimized for foodweb.ai):
1. `search_recipes()` - Find recipes by name/kitchen
2. `get_recipe_details()` - Full recipe with ingredients & sub-recipes
3. `create_recipe()` - Add new recipes
4. `add_ingredient_to_recipe()` - Add ingredients with amounts
5. `list_ingredients()` - Browse inventory

### All Tools Use Optional Parameters:
- Most parameters are optional
- Smart defaults applied
- Easy voice interaction

## Deployment Steps:

### 1. Deploy to LangGraph Cloud
```bash
cd /home/yotambg/Documents/foodie-stuff/roa-voice/agent
langgraph up
```

### 2. Set Environment Variables (LangGraph Cloud):
- `NEO4J_URI` - Your Neo4j cloud instance
- `NEO4J_USER` - neo4j
- `NEO4J_PASSWORD` - your password
- `GOOGLE_API_KEY` - Already set

### 3. Get Neo4j Cloud Instance:
- Go to https://neo4j.com/cloud/aura/
- Create free AuraDB instance
- Load production data using `migrate_production_v2.py`

## Local Testing Passed ✅:
- Search recipes
- Get full details
- Create recipes
- Add ingredients
- List inventory

## Next: Deploy when ready!
