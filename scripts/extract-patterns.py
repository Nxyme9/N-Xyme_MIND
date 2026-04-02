#!/usr/bin/env python3
"""Pattern Extractor - Self-Learning System Component"""

import json, subprocess, sys, re
from datetime import datetime
from collections import defaultdict
from typing import Optional

GRAPHITI_URL = "http://localhost:8001/json-rpc"
OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_LIMIT = 50
DEFAULT_THRESHOLD = 0.8
OLLAMA_MODEL = "qwen2.5-coder:7b"


def graphiti_rpc(method: str, params: dict) -> dict:
    payload = {"jsonrpc": "2.0", "method": method, "params": params, "id": 1}
    result = subprocess.run(
        [
            "curl",
            "-s",
            "-X",
            "POST",
            GRAPHITI_URL,
            "-H",
            "Content-Type: application/json",
            "-d",
            json.dumps(payload),
        ],
        capture_output=True,
        text=True, encoding='utf-8', errors='replace',
        timeout=30,
    )
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"error": result.stdout}


def get_episodes(limit: int = DEFAULT_LIMIT) -> list:
    response = graphiti_rpc("graphiti_get_episodes", {"limit": limit, "offset": 0})
    episodes = response.get("result", {}).get("episodes", [])
    print(f"[INFO] Fetched {len(episodes)} episodes from Graphiti")
    return episodes


def get_existing_patterns() -> set:
    response = graphiti_rpc("graphiti_search_nodes", {"query": "source=pattern", "limit": 100})
    patterns = response.get("result", {}).get("episodes", [])
    pattern_ids = {p["id"] for p in patterns if p.get("id")}
    print(f"[INFO] Found {len(pattern_ids)} existing pattern episodes")
    return pattern_ids


def find_similar_episodes(episode: dict, threshold: float = 0.7) -> list:
    response = graphiti_rpc(
        "graphiti_vector_search", {"query": episode.get("text", "")[:200], "limit": 20}
    )
    try:
        result = response.get("result", {})
        content = result.get("content", [])
        if content and "text" in content[0]:
            data = json.loads(content[0]["text"])
            return data.get("episodes", data.get("results", []))
        return []
    except:
        return []


def compute_similarity_batch(episodes: list, threshold: float = DEFAULT_THRESHOLD) -> defaultdict:
    similar_map = defaultdict(list)
    non_pattern_episodes = [e for e in episodes if "pattern" not in e.get("text", "").lower()[:100]]

    print(f"[INFO] Computing similarities for {len(non_pattern_episodes)} episodes...")

    for i, episode in enumerate(non_pattern_episodes):
        if i % 10 == 0:
            print(f"[PROGRESS] Processed {i}/{len(non_pattern_episodes)} episodes")

        episode_id = episode.get("id")
        if not episode_id:
            continue

        similar = find_similar_episodes(episode, threshold)

        for sim_ep in similar:
            sim_id = sim_ep.get("id")
            score = sim_ep.get("score", 0)
            if sim_id and score >= threshold and sim_id != episode_id:
                similar_map[episode_id].append((sim_id, score))
                similar_map[sim_id].append((episode_id, score))

    print(f"[INFO] Found {sum(len(v) for v in similar_map.values()) // 2} similarity pairs")
    return similar_map


def cluster_episodes(similar_map: dict, episodes: list) -> list:
    episode_text = {e["id"]: e.get("text", "") for e in episodes}
    parent = {eid: eid for eid in episode_text.keys()}

    def find(x):
        if parent[x] != x:
            parent[x] = find(parent[x])
        return parent[x]

    def union(x, y):
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py

    for episode_id, similar_list in similar_map.items():
        for sim_id, score in similar_list:
            if score >= DEFAULT_THRESHOLD:
                union(episode_id, sim_id)

    clusters = defaultdict(list)
    for episode_id in episode_text:
        cluster_id = find(episode_id)
        if episode_text[episode_id]:
            clusters[cluster_id].append({"id": episode_id, "text": episode_text[episode_id]})

    valid_clusters = [c for c in clusters.values() if len(c) >= 2]
    print(f"[INFO] Found {len(valid_clusters)} clusters with 2+ episodes")
    return valid_clusters


def extract_pattern_with_llm(cluster: list) -> Optional[str]:
    if len(cluster) < 2:
        return None

    episodes_text = "\n\n".join(
        [f"Episode {i + 1}: {ep['text'][:300]}" for i, ep in enumerate(cluster)]
    )

    prompt = f"""You are a pattern recognition system. Analyze the following episodes and identify a recurring pattern.

Guidelines:
- Temporal: "X always happens before Y"
- Causal: "X causes Y"
- Preference: "User always does X"  
- Error: "X always leads to error Y"
- Velocity: "Task type X takes Y minutes"

Respond with ONLY the pattern. If no clear pattern exists, respond with: NO_PATTERN

Episodes:
{episodes_text}

Pattern:"""

    try:
        result = subprocess.run(
            [
                "curl",
                "-s",
                "-X",
                "POST",
                OLLAMA_URL,
                "-H",
                "Content-Type: application/json",
                "-d",
                json.dumps(
                    {
                        "model": OLLAMA_MODEL,
                        "prompt": prompt,
                        "stream": False,
                        "options": {"temperature": 0.3, "top_p": 0.9},
                    }
                ),
            ],
            capture_output=True,
            text=True, encoding='utf-8', errors='replace',
            timeout=120,
        )

        response = json.loads(result.stdout)
        pattern = response.get("response", "").strip()
        pattern = re.sub(
            r"^(Pattern:|The pattern is:|Pattern:)\s*", "", pattern, flags=re.IGNORECASE
        )

        if pattern.upper() == "NO_PATTERN" or len(pattern) < 10:
            return None
        return pattern

    except Exception as e:
        print(f"[ERROR] LLM extraction failed: {e}")
        return None


def store_pattern(pattern: str, source_episodes: list) -> bool:
    metadata = {
        "type": "pattern",
        "source": "pattern",
        "derived_from": [ep["id"] for ep in source_episodes[:5]],
        "extracted_at": datetime.utcnow().isoformat(),
        "cluster_size": len(source_episodes),
    }

    response = graphiti_rpc(
        "graphiti_add_episode", {"text": pattern, "metadata": json.dumps(metadata)}
    )

    success = response.get("result", {}).get("success", False)
    if success:
        episode_id = response.get("result", {}).get("episodeId", "unknown")
        print(f"[STORED] Pattern: {pattern[:80]}... (ID: {episode_id})")
    else:
        print(f"[ERROR] Failed to store pattern: {pattern[:50]}...")

    return success


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Extract patterns from Graphiti episodes")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT, help="Max episodes to process")
    parser.add_argument(
        "--threshold", type=float, default=DEFAULT_THRESHOLD, help="Similarity threshold"
    )
    args = parser.parse_args()

    print("=" * 60)
    print("PATTERN EXTRACTOR - Self-Learning System")
    print("=" * 60)
    print(f"Limit: {args.limit}, Threshold: {args.threshold}")
    print()

    episodes = get_episodes(args.limit)
    if not episodes:
        print("[ERROR] No episodes found in Graphiti")
        sys.exit(1)

    existing_patterns = get_existing_patterns()
    similar_map = compute_similarity_batch(episodes, args.threshold)
    clusters = cluster_episodes(similar_map, episodes)

    print("\n[INFO] Extracting patterns from clusters...")
    patterns_found = 0
    patterns_stored = 0

    for i, cluster in enumerate(clusters):
        cluster_ids = {ep["id"] for ep in cluster}
        if cluster_ids & existing_patterns:
            print(f"[SKIP] Cluster {i + 1}: contains existing pattern")
            continue

        print(f"\n[CLUSTER {i + 1}] {len(cluster)} episodes:")
        for ep in cluster[:3]:
            print(f"  - {ep['text'][:80]}...")

        pattern = extract_pattern_with_llm(cluster)
        if pattern:
            patterns_found += 1
            print(f"  -> Pattern: {pattern[:100]}")

            if store_pattern(pattern, cluster):
                patterns_stored += 1
                existing_patterns.add(f"pattern_{patterns_stored}")
        else:
            print(f"  -> No clear pattern found")

    print("\n" + "=" * 60)
    print(f"SUMMARY: Found {patterns_found} patterns, stored {patterns_stored} new patterns")
    print("=" * 60)


if __name__ == "__main__":
    main()
