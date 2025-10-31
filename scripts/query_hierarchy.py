#!/usr/bin/env python3
"""Query LangSmith to get complete hierarchical run tree with all nested children"""

import os
from langsmith import Client
from datetime import datetime, timedelta
import json
from collections import defaultdict

# Set API key
# API key loaded from environment variable

# Initialize client
client = Client()

# Create output file
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
output_file = f"ROA-CONVOS/hierarchy_{timestamp}.txt"

print("🔍 Fetching complete hierarchical run tree from LangSmith...")

def print_run_tree(run, all_runs_dict, f, depth=0):
    """Recursively print run and all children in tree format"""
    print(f"  {'  ' * depth}Processing run: {run.name} (depth={depth})")
    
    indent = "  " * depth
    
    # Tree characters
    if depth == 0:
        prefix = "🌳 "
    else:
        prefix = "├─ "
    
    f.write(f"{indent}{prefix}[{run.run_type.upper()}] {run.name}\n")
    f.write(f"{indent}   ID: {run.id}\n")
    f.write(f"{indent}   Duration: {run.end_time - run.start_time if run.end_time else 'Running...'}\n")
    f.write(f"{indent}   Status: {run.status}\n")
    
    print(f"  {'  ' * depth}  - Writing basic info")
    
    # Show inputs (abbreviated)
    print(f"  {'  ' * depth}  - Processing inputs")
    if run.inputs:
        f.write(f"{indent}   📥 Inputs: ")
        try:
            if isinstance(run.inputs, dict):
                if 'messages' in run.inputs and run.inputs['messages']:
                    msgs = run.inputs['messages']
                    if isinstance(msgs, list) and len(msgs) > 0:
                        last_msg = msgs[-1]
                        if isinstance(last_msg, dict) and 'content' in last_msg:
                            content = last_msg['content'][:100]
                            f.write(f"'{content}...'\n")
                        else:
                            f.write(f"{str(msgs[-1])[:100]}...\n")
                    else:
                        f.write(f"{str(run.inputs)[:100]}...\n")
                else:
                    f.write(f"{str(run.inputs)[:100]}...\n")
            else:
                f.write(f"{str(run.inputs)[:100]}...\n")
        except Exception as e:
            f.write(f"[Error displaying inputs: {e}]\n")
    
    print(f"  {'  ' * depth}  - Processing outputs")
    # Show outputs (abbreviated)
    if run.outputs:
        f.write(f"{indent}   📤 Outputs: ")
        try:
            if isinstance(run.outputs, dict):
                if 'messages' in run.outputs and run.outputs['messages']:
                    msgs = run.outputs['messages']
                    if isinstance(msgs, list) and len(msgs) > 0:
                        last_msg = msgs[-1]
                        if isinstance(last_msg, dict) and 'content' in last_msg:
                            content = last_msg['content'][:200]
                            f.write(f"'{content}...'\n")
                        else:
                            f.write(f"{str(msgs[-1])[:200]}...\n")
                    else:
                        f.write(f"{str(run.outputs)[:200]}...\n")
                elif 'output' in run.outputs:
                    f.write(f"{str(run.outputs['output'])[:200]}...\n")
                else:
                    f.write(f"{str(run.outputs)[:200]}...\n")
            else:
                f.write(f"{str(run.outputs)[:200]}...\n")
        except Exception as e:
            f.write(f"[Error displaying outputs: {e}]\n")
    
    # Show error if any
    if run.error:
        f.write(f"{indent}   ❌ ERROR: {run.error[:200]}\n")
    
    f.write(f"{indent}\n")
    
    # Find and print all children
    print(f"  {'  ' * depth}  - Finding children")
    children = [r for r in all_runs_dict.values() if r.parent_run_id == run.id]
    print(f"  {'  ' * depth}  - Found {len(children)} children")
    # Sort children by start time
    children.sort(key=lambda r: r.start_time)
    
    for child in children:
        print_run_tree(child, all_runs_dict, f, depth + 1)


print("Opening output file...")
with open(output_file, 'w') as f:
    print("Writing header...")
    f.write("🌳 COMPLETE HIERARCHICAL RUN TREE\n")
    f.write("=" * 100 + "\n\n")
    
    # Get recent root runs (last 24 hours)
    print("Fetching root runs from LangSmith...")
    root_runs = list(client.list_runs(
        project_name="roa-voice-dev",
        start_time=datetime.now() - timedelta(hours=24),
        is_root=True,
        limit=15  # Get more to see all the duplicates
    ))
    
    print(f"Retrieved {len(root_runs)} root runs")
    
    if not root_runs:
        f.write("No runs found in the last 24 hours\n")
        print("❌ No runs found")
        exit()
    
    print(f"Processing {len(root_runs)} root runs...")
    f.write(f"📊 Found {len(root_runs)} root-level runs\n")
    f.write(f"⏰ Time range: {root_runs[-1].start_time} to {root_runs[0].start_time}\n")
    f.write("=" * 100 + "\n\n")
    
    # Process each root run
    for i, root_run in enumerate(root_runs, 1):
        print(f"\n{'='*50}")
        print(f"Processing TRACE #{i}/{len(root_runs)}")
        print(f"Trace ID: {root_run.trace_id}")
        print(f"{'='*50}")
        
        f.write(f"\n{'=' * 100}\n")
        f.write(f"TRACE #{i} - {root_run.start_time}\n")
        f.write(f"{'=' * 100}\n\n")
        
        # Get ALL runs for this trace
        print(f"Fetching all runs for trace {root_run.trace_id}...")
        all_runs = list(client.list_runs(trace_id=root_run.trace_id))
        print(f"Retrieved {len(all_runs)} runs for this trace")
        
        # Create dict for quick lookup
        print("Creating run dictionary...")
        all_runs_dict = {run.id: run for run in all_runs}
        print(f"Dictionary created with {len(all_runs_dict)} entries")
        
        f.write(f"Total runs in this trace: {len(all_runs)}\n")
        f.write(f"Trace ID: {root_run.trace_id}\n")
        f.write(f"Duration: {root_run.end_time - root_run.start_time if root_run.end_time else 'N/A'}\n\n")
        
        # Print the tree starting from root
        print(f"Starting tree traversal for trace #{i}...")
        print_run_tree(root_run, all_runs_dict, f, depth=0)
        print(f"Completed tree traversal for trace #{i}")
        
        # Summary for this trace
        print(f"Writing summary for trace #{i}...")
        f.write(f"\n{'─' * 100}\n")
        f.write(f"📊 TRACE #{i} SUMMARY:\n")
        
        # Count by run_type
        run_types = defaultdict(int)
        for run in all_runs:
            run_types[run.run_type] += 1
        
        f.write(f"Run types: ")
        f.write(", ".join([f"{rt}={count}" for rt, count in sorted(run_types.items())]))
        f.write(f"\n")
        
        # Find errors
        errors = [r for r in all_runs if r.error]
        if errors:
            f.write(f"⚠️  Errors: {len(errors)}\n")
            for err_run in errors:
                f.write(f"  - {err_run.name}: {err_run.error[:150]}\n")
        
        # Check for limitation messages
        limitation_msgs = []
        for run in all_runs:
            if run.outputs and isinstance(run.outputs, dict):
                outputs_str = str(run.outputs).lower()
                if any(keyword in outputs_str for keyword in ['cannot', "can't", 'unable to', "don't have", "do not have"]):
                    limitation_msgs.append((run.name, run.outputs))
        
        if limitation_msgs:
            f.write(f"⚠️  Limitation messages detected: {len(limitation_msgs)}\n")
            for name, outputs in limitation_msgs:
                f.write(f"  - {name}: {str(outputs)[:200]}...\n")
        
        f.write(f"\n")
    
    # Overall summary
    print("\nWriting overall summary...")
    f.write(f"\n{'=' * 100}\n")
    f.write(f"🎯 OVERALL SUMMARY\n")
    f.write(f"{'=' * 100}\n")
    f.write(f"Total traces analyzed: {len(root_runs)}\n")
    
    # Check for identical runs (potential loops)
    identical_outputs = defaultdict(list)
    for root_run in root_runs:
        if root_run.outputs:
            output_key = str(root_run.outputs)[:500]  # Use first 500 chars as key
            identical_outputs[output_key].append(root_run.id)
    
    duplicates = {k: v for k, v in identical_outputs.items() if len(v) > 1}
    if duplicates:
        f.write(f"\n⚠️  DUPLICATE OUTPUTS DETECTED (potential loop):\n")
        for output_key, run_ids in duplicates.items():
            f.write(f"  - {len(run_ids)} runs with same output:\n")
            f.write(f"    Output preview: {output_key[:150]}...\n")
            f.write(f"    Run IDs: {run_ids}\n\n")

print(f"✅ Saved complete hierarchy to: {output_file}")
