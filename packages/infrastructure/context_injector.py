#!/usr/bin/env python3
"""
Context Injector for OpenCode
Connects OpenCode to Neo4j/Graphiti memory for automatic context injection
"""

import json
import logging
import requests
from typing import List, Optional
from datetime import datetime

logger = logging.getLogger("context-injector")

GRAPHITI_URL = "http://localhost:8001/json-rpc"
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "neo4j"


def get_startup_context(project_path: str = None) -> str:
    """Get context to inject at session start"""
    context_parts = []
    
    try:
        resp = requests.post(
            GRAPHITI_URL,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "graphiti_get_episodes",
                "params": {"group_id": "chain-runs", "last_n": 5}
            },
            timeout=5
        )
        if resp.status_code == 200:
            episodes = resp.json().get("result", {}).get("episodes", [])
            if episodes:
                context_parts.append("## Recent Memory")
                for ep in episodes[:3]:
                    context_parts.append(f"- {ep.get('name', 'Unknown')}: {ep.get('text', '')[:100]}...")
    except Exception as e:
        logger.warning(f"Failed to get Graphiti context: {e}")
    
    if project_path:
        try:
            resp = requests.post(
                GRAPHITI_URL,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "graphiti_hybrid_search",
                    "params": {"query": project_path, "max_results": 3}
                },
                timeout=5
            )
            if resp.status_code == 200:
                results = resp.json().get("result", {}).get("episodes", [])
                if results:
                    context_parts.append(f"\n## Project Context ({project_path})")
                    for ep in results:
                        context_parts.append(f"- {ep.get('text', '')[:150]}...")
        except Exception as e:
            logger.warning(f"Failed to get project context: {e}")
    
    if not context_parts:
        return ""
    
    return "\n".join(context_parts)


def search_memory(query: str, max_results: int = 5) -> List[dict]:
    """Search memory for specific query"""
    results = []
    
    try:
        resp = requests.post(
            GRAPHITI_URL,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "graphiti_hybrid_search",
                "params": {"query": query, "max_results": max_results}
            },
            timeout=5
        )
        if resp.status_code == 200:
            episodes = resp.json().get("result", {}).get("episodes", [])
            for ep in episodes:
                results.append({
                    "source": "graphiti",
                    "text": ep.get("text", ""),
                    "timestamp": ep.get("created", "")
                })
    except Exception as e:
        logger.warning(f"Memory search failed: {e}")
    
    return results


def store_decision(decision: str, context: str = "", tags: List[str] = None) -> bool:
    """Store a decision in memory"""
    try:
        text = f"Decision: {decision}"
        if context:
            text += f"\nContext: {context}"
        if tags:
            text += f"\nTags: {', '.join(tags)}"
        
        resp = requests.post(
            GRAPHITI_URL,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "graphiti_add_episode",
                "params": {
                    "name": f"decision-{datetime.now().isoformat()}",
                    "text": text,
                    "source": "opencode",
                    "group_id": "decisions"
                }
            },
            timeout=5
        )
        return resp.status_code == 200
    except Exception as e:
        logger.warning(f"Failed to store decision: {e}")
        return False


def store_pattern(pattern_name: str, description: str, code_snippet: str = "") -> bool:
    """Store a learned pattern in memory"""
    try:
        text = f"Pattern: {pattern_name}\n{description}"
        if code_snippet:
            text += f"\n```{code_snippet}```"
        
        resp = requests.post(
            GRAPHITI_URL,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "graphiti_add_episode",
                "params": {
                    "name": f"pattern-{pattern_name}",
                    "text": text,
                    "source": "opencode",
                    "group_id": "patterns"
                }
            },
            timeout=5
        )
        return resp.status_code == 200
    except Exception as e:
        logger.warning(f"Failed to store pattern: {e}")
        return False


if __name__ == "__main__":
    print("Testing context injector...")
    
    print("\n1. Startup context:")
    print(get_startup_context())
    
    print("\n2. Search memory:")
    results = search_memory("agent")
    for r in results:
        print(f"  - {r['text'][:100]}...")
    
    print("\n3. Store decision:")
    success = store_decision("Test decision", "Testing context injector", ["test", "memory"])
    print(f"  Stored: {success}")
    
    print("\nDone!")
