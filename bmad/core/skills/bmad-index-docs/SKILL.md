---
name: bmad-index-docs
description: Generates or updates an index.md to reference all docs in the folder. Use when user says "create index" or "update index" in a folder.
argument-hint: "[folder-path] [overwrite]"
---

# Index Docs — Document Index Generator

## Overview
Scan a folder and generate or update an index.md that references all documents within. Creates a navigable directory of documentation.

## On Activation
1. **Scan folder.** List all files recursively.
2. **Read frontmatter.** Extract title, description from each.
3. **Build index.** Create index.md with hierarchical structure.

## Index Format
```
# {folder-name} — Index

## Category 1
- [Document Title](./path/to/doc.md) — Brief description
- [Another Doc](./path/to/doc2.md) — Brief description

## Category 2
...
```

## Options
- `overwrite=true` — Replace existing index.md
- `overwrite=false` — Append new entries only