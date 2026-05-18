---
name: bmad-shard-doc
description: Splits large markdown documents into smaller, organized files. Use when user says "shard this document" or "split this file".
argument-hint: "[document-path] [section-level] [output-dir]"
---

# Shard Doc — Document Splitting

## Overview
Split a large markdown document into smaller files based on heading levels. Each section becomes a separate file with a linking index.

## On Activation
1. **Parse document.** Read markdown, identify heading structure.
2. **Split.** Create one file per heading at the specified level.
3. **Index.** Create a parent index.md linking all shards.
4. **Preserve.** Keep frontmatter, cross-references intact.

## Options
- `section-level=2` — Split at ## headings (default)
- `section-level=3` — Split at ### headings (finer)
- `output-dir` — Where to write the shards

## Output
```
output-dir/
├── index.md           ← linking all shards
├── 01-section-name.md
├── 02-section-name.md
└── ...
```

Each shard preserves the parent heading context.