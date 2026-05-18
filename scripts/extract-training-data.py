#!/usr/bin/env python3
import json
import os
from pathlib import Path

PROJECT_ROOT = "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND"
OUTPUT_PATH = os.path.join(PROJECT_ROOT, "data/training/mojo_rosetta.jsonl")

os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

training_data = []

# 1. Extract from archive
archive_dir = os.path.join(PROJECT_ROOT, "archive/data_chaos/data_chaos")
if os.path.exists(archive_dir):
    for root, dirs, files in os.walk(archive_dir):
        for f in files:
            if f.endswith('.jsonl'):
                try:
                    with open(os.path.join(root, f)) as fp:
                        for line in fp:
                            try:
                                entry = json.loads(line.strip())
                                if isinstance(entry, dict) and 'tool' in entry and 'params' in entry:
                                    training_data.append({
                                        "source": "archive",
                                        "query": json.dumps(entry.get('params', {})),
                                        "expected_tool": entry['tool'],
                                        "context": json.dumps(entry)
                                    })
                            except:
                                pass
                except:
                    pass

# 2. Extract from session data
sessions_dir = os.path.join(PROJECT_ROOT, "data/sessions")
if os.path.exists(sessions_dir):
    for root, dirs, files in os.walk(sessions_dir):
        for f in files:
            if f.endswith('.jsonl'):
                try:
                    with open(os.path.join(root, f)) as fp:
                        for line in fp:
                            try:
                                entry = json.loads(line.strip())
                                if 'tool' in entry and 'params' in entry:
                                    training_data.append({
                                        "source": "session",
                                        "query": json.dumps(entry.get('params', {}))[:500],
                                        "expected_tool": entry['tool'],
                                        "context": json.dumps(entry)[:1000]
                                    })
                            except:
                                pass
                except:
                    pass

# 3. Extract from ingest.jsonl
ingest_path = os.path.join(PROJECT_ROOT, "data/memory/vectors/ingest.jsonl")
if os.path.exists(ingest_path):
    with open(ingest_path) as fp:
        for line in fp:
            try:
                entry = json.loads(line.strip())
                content = entry.get('content', '')
                if 'query:' in content:
                    training_data.append({
                        "source": "memory",
                        "query": content.replace('query:', ''),
                        "expected_tool": "memory_search",
                        "context": json.dumps(entry)[:500]
                    })
            except:
                pass

# Write training data
with open(OUTPUT_PATH, "w") as f:
    for item in training_data:
        f.write(json.dumps(item) + "\n")

print(f"Extracted {len(training_data)} training examples to {OUTPUT_PATH}")
print(f"Sources: archives={sum(1 for t in training_data if t['source']=='archive')}, sessions={sum(1 for t in training_data if t['source']=='session')}, memory={sum(1 for t in training_data if t['source']=='memory')}")
