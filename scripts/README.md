# 🔧 Scripts

Utility scripts for debugging and analyzing ROA agent behavior.

## LangSmith Query Scripts

These scripts connect to LangSmith to fetch and analyze conversation traces:

- **`query_langsmith.py`** - Fetch recent runs (basic overview)
- **`query_full_trace.py`** - Get complete trace with all child runs
- **`query_hierarchy.py`** - Full hierarchical tree view of traces (MOST DETAILED)
- **`query_single_trace.py`** - Quick single trace analysis
- **`query_detailed.py`** - Detailed view of specific run ID

## Deployment Scripts

- **`check_deployment.py`** - Check LangGraph deployment status

## Usage

All scripts use the LangSmith API key from environment. Set it before running:

```bash
export LANGSMITH_API_KEY="lsv2_pt_..."
```

Or the scripts will use the hardcoded key (already configured).

### Example:

```bash
# Get full hierarchical trace analysis
python3 query_hierarchy.py

# Output saved to: ../ROA-CONVOS/hierarchy_[timestamp].txt
```

## Output Directory

All conversation logs are saved to: `../ROA-CONVOS/`
