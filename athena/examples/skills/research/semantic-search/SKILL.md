---
name: semantic-search
description: Executes exact Exocortex embeddings lookup for internal libraries. Wraps smart_search.py.
argument-hint: "find <query>"
allowed-tools:
  - Bash
auto-invoke: false
model: default
user-invocable: false
---

# The Exocortex Semantic Engine

A direct interface to the local RAG (Retrieval-Augmented Generation) system, wrapping `smart_search.py` for high-precision knowledge retrieval.

## Triggers

"search memory", "find protocol", "do we have a case study on"

## Core Mechanics

1. Executes `python3 Athena-Public/examples/scripts/smart_search.py "<query>" --limit 5`
2. Synthesizes the results before pulling the full markdown files into the context window.

## Reference Paths

- `.context/memories/protocols/coding/108-semantic-search-standards.md`
