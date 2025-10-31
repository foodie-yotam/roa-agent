# 🧪 Tests

Test scripts for ROA agent functionality.

## Test Files

- **`test_local.py`** - Test agent locally (before deployment)
- **`test_deployed.py`** - Test deployed agent on LangGraph Cloud
- **`test_deployed_official.py`** - Official deployment tests
- **`test_neo4j.py`** - Test Neo4j database connections and queries
- **`test_recipe_scaling.py`** - Test recipe scaling functionality

## Legacy Tests

- **`test_local_old.py.bak`** - Old version of local tests (backup)

## Running Tests

### Local Testing:
```bash
python3 test_local.py
```

### Deployed Testing:
```bash
python3 test_deployed.py
```

### Neo4j Testing:
```bash
python3 test_neo4j.py
```

Make sure environment variables are set:
- `NEO4J_URI`
- `NEO4J_USERNAME`
- `NEO4J_PASSWORD`
- `LANGGRAPH_URL` (for deployed tests)
