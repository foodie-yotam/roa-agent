#!/usr/bin/env python3
"""Query LangSmith to get FULL trace with all child runs, logs, and metrics"""

import os
from langsmith import Client
from datetime import datetime, timedelta
import json

# Set API key
# API key loaded from environment variable

# Initialize client
client = Client()

# Create output file
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
output_file = f"ROA-CONVOS/full_trace_{timestamp}.txt"

print("🔍 Fetching FULL trace with all child runs from LangSmith...")

with open(output_file, 'w') as f:
    f.write("🔍 FULL ROA Trace - Complete Conversation with All Steps\n")
    f.write("=" * 100 + "\n\n")
    
    # Get most recent root run
    root_runs = list(client.list_runs(
        project_name="roa-voice-dev",
        start_time=datetime.now() - timedelta(hours=24),
        is_root=True,
        limit=1  # Just get the most recent
    ))
    
    if not root_runs:
        f.write("No runs found in the last 24 hours\n")
        print("❌ No runs found")
        exit()
    
    root_run = root_runs[0]
    trace_id = root_run.trace_id
    
    f.write(f"🌳 TRACE ID: {trace_id}\n")
    f.write(f"📅 Started: {root_run.start_time}\n")
    f.write(f"⏱️ Duration: {root_run.end_time - root_run.start_time if root_run.end_time else 'N/A'}\n")
    f.write(f"✅ Status: {root_run.status}\n")
    f.write("=" * 100 + "\n\n")
    
    # Get ALL runs in this trace (including children)
    all_runs = list(client.list_runs(
        trace_id=trace_id,
        # Don't filter by is_root - get EVERYTHING
    ))
    
    f.write(f"📊 Total runs in trace: {len(all_runs)}\n")
    f.write("=" * 100 + "\n\n")
    
    # Sort by start time to show chronological order
    sorted_runs = sorted(all_runs, key=lambda r: r.start_time)
    
    # Display each run with full details
    for i, run in enumerate(sorted_runs, 1):
        # Determine depth based on parent_run_id
        depth = 0
        temp_run = run
        while temp_run.parent_run_id:
            depth += 1
            # Find parent
            parent = next((r for r in all_runs if r.id == temp_run.parent_run_id), None)
            if not parent:
                break
            temp_run = parent
        
        indent = "  " * depth
        
        f.write(f"\n{'─' * 100}\n")
        f.write(f"{indent}[{i}] 📦 {run.name} ({run.run_type})\n")
        f.write(f"{indent}    ID: {run.id}\n")
        f.write(f"{indent}    Parent: {run.parent_run_id or 'ROOT'}\n")
        f.write(f"{indent}    Start: {run.start_time}\n")
        f.write(f"{indent}    Duration: {run.end_time - run.start_time if run.end_time else 'Running...'}\n")
        f.write(f"{indent}    Status: {run.status}\n")
        
        # Show inputs
        if run.inputs:
            f.write(f"\n{indent}    📥 INPUTS:\n")
            try:
                inputs_str = json.dumps(run.inputs, indent=8, default=str)
                # Show first 1000 chars
                if len(inputs_str) > 1000:
                    f.write(f"{indent}    {inputs_str[:1000]}...\n")
                else:
                    f.write(f"{indent}    {inputs_str}\n")
            except:
                f.write(f"{indent}    {str(run.inputs)[:1000]}\n")
        
        # Show outputs
        if run.outputs:
            f.write(f"\n{indent}    📤 OUTPUTS:\n")
            try:
                outputs_str = json.dumps(run.outputs, indent=8, default=str)
                # Show first 1000 chars
                if len(outputs_str) > 1000:
                    f.write(f"{indent}    {outputs_str[:1000]}...\n")
                else:
                    f.write(f"{indent}    {outputs_str}\n")
            except:
                f.write(f"{indent}    {str(run.outputs)[:1000]}\n")
        
        # Show error if any
        if run.error:
            f.write(f"\n{indent}    ❌ ERROR:\n")
            f.write(f"{indent}    {run.error}\n")
        
        # Show metadata
        if hasattr(run, 'extra') and run.extra:
            if 'metadata' in run.extra and run.extra['metadata']:
                f.write(f"\n{indent}    🏷️ METADATA:\n")
                try:
                    metadata_str = json.dumps(run.extra['metadata'], indent=8, default=str)
                    if len(metadata_str) > 500:
                        f.write(f"{indent}    {metadata_str[:500]}...\n")
                    else:
                        f.write(f"{indent}    {metadata_str}\n")
                except:
                    f.write(f"{indent}    {str(run.extra['metadata'])[:500]}\n")
        
        # Show tags
        if run.tags:
            f.write(f"\n{indent}    🏷️ TAGS: {', '.join(run.tags)}\n")
    
    f.write(f"\n{'=' * 100}\n")
    f.write("✅ Full trace export complete!\n")
    
    # Create summary
    f.write(f"\n{'=' * 100}\n")
    f.write("📊 SUMMARY\n")
    f.write(f"{'=' * 100}\n")
    f.write(f"Total runs: {len(all_runs)}\n")
    
    # Count by run_type
    run_types = {}
    for run in all_runs:
        run_types[run.run_type] = run_types.get(run.run_type, 0) + 1
    
    f.write(f"\nRun types breakdown:\n")
    for run_type, count in sorted(run_types.items()):
        f.write(f"  - {run_type}: {count}\n")
    
    # Find any errors
    errors = [run for run in all_runs if run.error]
    if errors:
        f.write(f"\n⚠️ Runs with errors: {len(errors)}\n")
        for error_run in errors:
            f.write(f"  - {error_run.name}: {error_run.error[:200]}\n")
    
    # Calculate total duration
    if root_run.end_time:
        total_duration = root_run.end_time - root_run.start_time
        f.write(f"\n⏱️ Total trace duration: {total_duration}\n")

print(f"✅ Saved full trace to: {output_file}")
print(f"📊 Total runs captured: {len(all_runs)}")
