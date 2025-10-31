#!/usr/bin/env python3
"""Query a single trace to debug quickly"""

import os
from langsmith import Client
from datetime import datetime, timedelta

# Set API key
# API key loaded from environment variable

# Initialize client
client = Client()

print("🔍 Fetching ONE recent trace from LangSmith...")

# Get most recent root run
print("Step 1: Fetching root run...")
root_runs = list(client.list_runs(
    project_name="roa-voice-dev",
    start_time=datetime.now() - timedelta(hours=24),
    is_root=True,
    limit=1  # Just ONE
))

if not root_runs:
    print("❌ No runs found")
    exit()

root_run = root_runs[0]
print(f"✅ Found root run: {root_run.id}")
print(f"   Name: {root_run.name}")
print(f"   Start: {root_run.start_time}")

# Get ALL runs in this trace
print(f"\nStep 2: Fetching all runs for trace {root_run.trace_id}...")
all_runs = list(client.list_runs(trace_id=root_run.trace_id))
print(f"✅ Found {len(all_runs)} runs in this trace")

# List all runs
print(f"\nStep 3: Listing all {len(all_runs)} runs:")
for i, run in enumerate(sorted(all_runs, key=lambda r: r.start_time), 1):
    parent_info = f"(parent: {str(run.parent_run_id)[:8]}...)" if run.parent_run_id else "(ROOT)"
    print(f"  [{i}] {run.name} ({run.run_type}) {parent_info}")
    
    # Show brief outputs
    if run.outputs:
        if isinstance(run.outputs, dict):
            if 'messages' in run.outputs:
                msgs = run.outputs.get('messages', [])
                if msgs and isinstance(msgs, list):
                    last_msg = msgs[-1]
                    if isinstance(last_msg, dict) and 'content' in last_msg:
                        content = last_msg['content'][:150]
                        print(f"      Output: '{content}...'")

print(f"\n✅ Done! Total runs: {len(all_runs)}")
