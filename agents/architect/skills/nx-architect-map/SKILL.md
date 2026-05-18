---
name: nx-architect-map
description: "System Architect — Map full project architecture by reading live source files."
---

# nx-architect-map

Map the full system architecture by reading live source files. Read directory trees, config files, and key source files to build an accurate picture.

## Strategy
1. Read project root structure
2. Read config files (opencode.json, nx_agents.json, etc.)
3. Read key source entry points
4. Cross-reference file modification times to detect changes
5. Report concrete data: file sizes, line counts, last modified

## Always
Report timestamps and file sizes. Never rely on static knowledge — read live files.
