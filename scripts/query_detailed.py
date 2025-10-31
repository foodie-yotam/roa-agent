#!/usr/bin/env python3
"""Get detailed view of a specific LangSmith run"""

import os
from langsmith import Client
import json

# Set API key
# API key loaded from environment variable

# Initialize client
client = Client()

# Get the most recent run
run_id = "019a3b4e-7114-752f-b92b-25ff5aa9dde4"

print(f"🔍 Fetching detailed run: {run_id}")
print("=" * 70)

# Get the full run with all children
run = client.read_run(run_id)

print(f"\n📋 Run: {run.name}")
print(f"Status: {run.status}")
print(f"Start: {run.start_time}")
print(f"Duration: {run.end_time - run.start_time if run.end_time else 'N/A'}")

# Get all child runs
child_runs = list(client.list_runs(trace_id=run.trace_id))

print(f"\n🌳 Trace contains {len(child_runs)} total runs")
print("=" * 70)

# Display all runs in chronological order
for i, child_run in enumerate(sorted(child_runs, key=lambda r: r.start_time), 1):
    print(f"\n{'─' * 70}")
    print(f"[{i}] {child_run.name} ({child_run.run_type})")
    print(f"    ID: {child_run.id}")
    
    # Show inputs
    if child_run.inputs:
        print(f"\n    📥 INPUTS:")
        inputs_str = json.dumps(child_run.inputs, indent=6, default=str)
        # Limit output
        if len(inputs_str) > 500:
            print(f"    {inputs_str[:500]}...")
        else:
            print(f"    {inputs_str}")
    
    # Show outputs
    if child_run.outputs:
        print(f"\n    📤 OUTPUTS:")
        outputs_str = json.dumps(child_run.outputs, indent=6, default=str)
        # Limit output
        if len(outputs_str) > 500:
            print(f"    {outputs_str[:500]}...")
        else:
            print(f"    {outputs_str}")
    
    # Show error if any
    if child_run.error:
        print(f"\n    ❌ ERROR: {child_run.error}")

print(f"\n{'=' * 70}")
print("✅ Detailed query complete!")
