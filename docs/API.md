# N-Xyme_MIND API Documentation

> Auto-generated API reference for the N-Xyme_MIND REST API.

## Overview

The API provides HTTP endpoints for interacting with the memory system, brain modules, audio processing, and system management.

**Base URL**: `http://localhost:8000` (configurable)

---

## Endpoints

### System

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/system/health` | System health check |
| GET | `/api/system/status` | System status and metrics |
| POST | `/api/system/restart` | Restart system components |
| GET | `/api/system/config` | Get current configuration |

### Brain

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/brain/context` | Get current brain context |
| POST | `/api/brain/analyze` | Analyze input with brain modules |
| GET | `/api/brain/memory` | Query brain memory systems |
| POST | `/api/brain/learn` | Trigger learning cycle |

### Audio

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/audio/synthesize` | Synthesize audio from text |
| GET | `/api/audio/status` | Audio system status |

---

## Authentication

All API endpoints require authentication via API key in the `Authorization` header:

```
Authorization: Bearer <api-key>
```

## Error Responses

All errors follow a consistent format:

```json
{
  "error": "error_code",
  "message": "Human-readable description",
  "details": {}
}
```

| Status Code | Meaning |
|-------------|---------|
| 400 | Bad Request — invalid input |
| 401 | Unauthorized — missing/invalid API key |
| 404 | Not Found — endpoint doesn't exist |
| 500 | Internal Server Error — system failure |

---

## MCP Tools

The system also exposes functionality via MCP (Model Context Protocol) servers:

| MCP Server | Tools | Description |
|------------|-------|-------------|
| unified-memory | search_memories, create_memory, update_memory, delete_memory, get_memory_stats, recall_session, find_context, tempr_search, get_learning_stats, get_skill_status, record_skill_outcome, get_learning_patterns, evolve_prompt | Memory system operations |
| context7 | resolve-library-id, query-docs | Library documentation lookup |
| github | list_issues, create_pr, get_commit, search_code | GitHub operations |

---

*Generated: 2026-04-06*
