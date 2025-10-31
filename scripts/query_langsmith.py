#!/usr/bin/env python3
"""Query recent LangSmith runs to view ROA conversations"""

import os
from langsmith import Client
from datetime import datetime, timedelta

# Set API key
# API key loaded from environment variable

# Initialize client
client = Client()

# Create output file
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
output_file = f"ROA-CONVOS/conversation_{timestamp}.txt"

with open(output_file, 'w') as f:
    f.write("🔍 Recent ROA Conversations from LangSmith\n")
    f.write("=" * 70 + "\n")
    
    # Query recent runs
    runs = client.list_runs(
        project_name="roa-voice-dev",  # Adjust if your project name is different
        start_time=datetime.now() - timedelta(hours=24),
        is_root=True,  # Only get root runs (not nested)
        limit=10
    )
    
    # Display runs
    for i, run in enumerate(runs, 1):
        f.write(f"\n{'='*70}\n")
        f.write(f"Run #{i}: {run.name}\n")
        f.write(f"ID: {run.id}\n")
        f.write(f"Start: {run.start_time}\n")
        f.write(f"Status: {run.status}\n")
        
        # Get inputs/outputs
        if run.inputs:
            f.write(f"\n📥 INPUT:\n")
            if 'messages' in run.inputs:
                for msg in run.inputs['messages']:
                    if isinstance(msg, dict):
                        role = msg.get('role', 'unknown')
                        content = msg.get('content', '')
                    elif isinstance(msg, tuple):
                        role = msg[0]
                        content = msg[1]
                    else:
                        role = 'unknown'
                        content = str(msg)
                    f.write(f"  [{role}]: {content[:200]}\n")
            else:
                f.write(f"  {run.inputs}\n")
        
        if run.outputs:
            f.write(f"\n📤 OUTPUT:\n")
            if 'messages' in run.outputs:
                messages = run.outputs['messages']
                if messages:
                    last_msg = messages[-1]
                    if hasattr(last_msg, 'content'):
                        f.write(f"  {last_msg.content[:500]}\n")
                    else:
                        f.write(f"  {last_msg}\n")
            else:
                f.write(f"  {run.outputs}\n")
        
        # Check for routing recommendations in metadata
        if hasattr(run, 'extra') and run.extra:
            if 'metadata' in run.extra:
                metadata = run.extra['metadata']
                if 'routing_recommendations' in metadata:
                    f.write(f"\n🧭 ROUTING RECOMMENDATIONS:\n")
                    f.write(f"  {metadata['routing_recommendations']}\n")

    f.write(f"\n{'='*70}\n")
    f.write("✅ Query complete!\n")

print(f"✅ Saved conversation to: {output_file}")
