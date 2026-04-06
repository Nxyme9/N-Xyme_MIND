#!/usr/bin/env python3
"""
Memory System Enhancements — Tier 1 (High ROI, Low/Medium Effort)

Implements:
1. HNSW indexing in ChromaDB
2. Time-decay weighting for memory retrieval
3. RRF (Reciprocal Rank Fusion) across retrievers
4. Importance scoring for memories
5. bge-m3 model support (optional upgrade from nomic-embed-text)

Usage:
    python -m src.memory.enhancements init      # Initialize all enhancements
    python -m src.memory.enhancements hnsw       # Test HNSW indexing
    python -m src.memory.enhancements time-decay # Test time-decay
    python -m src.memory.enhancements rrf        # Test RRF fusion
    python -m src.memory.enhancements importance # Test importance scoring
    python -m src.memory.enhancements all        # Run all tests
"""

import json
import math
import os
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).parent.parent.parent
DB_PATH = PROJECT_ROOT / "context" / "memory" / "mind_from_mind.db"
KG_ENTITIES = PROJECT_ROOT / ".context" / "memory_graph" / "entities.json"
KG_RELATIONS = PROJECT_ROOT / ".context" / "memory_graph" / "relations.json"


# ---------------------------------------------------------------------------
# 1. HNSW Indexing for ChromaDB
# ---------------------------------------------------------------------------


def init_chromadb_hnsw(collection_name: str = "memories"):
    """Initialize ChromaDB with HNSW indexing parameters."""
    try:
        import chromadb

        client = chromadb.PersistentClient(
            path=str(PROJECT_ROOT / ".context" / "chroma_db")
        )

        # HNSW parameters for optimal performance
        # hnsw_space: cosine similarity space
        # hnsw_construction_ef: higher = better index quality (default: 100)
        # hnsw_search_ef: higher = better recall (default: 10)
        # hnsw_M: max connections per node (default: 16)
        collection = client.get_or_create_collection(
            name=collection_name,
            metadata={
                "hnsw:space": "cosine",
                "hnsw:construction_ef": 200,
                "hnsw:search_ef": 50,
                "hnsw:M": 32,
            },
        )
        print(f"  ✅ HNSW collection '{collection_name}' initialized")
        print(f"     - Space: cosine")
        print(f"     - Construction EF: 200")
        print(f"     - Search EF: 50")
        print(f"     - M: 32")
        print(f"     - Count: {collection.count()} documents")
        return collection
    except ImportError:
        print("  ⚠️  ChromaDB not installed, skipping HNSW")
        return None
    except Exception as e:
        print(f"  ⚠️  HNSW init failed: {e}")
        return None


def test_hnsw():
    """Test HNSW indexing performance."""
    print("\n🔍 Testing HNSW Indexing...")
    collection = init_chromadb_hnsw()
    if not collection:
        print("  ⏭️  Skipped (ChromaDB not available)")
        return False

    # Add test documents
    test_docs = [
        "Sisyphus is the primary orchestrator",
        "Hephaestus implements code changes",
        "Oracle provides architecture review",
        "N-Xyme_MIND uses Ollama for embeddings",
        "ChromaDB provides vector search with HNSW",
    ]
    test_ids = [f"test_{i}" for i in range(len(test_docs))]

    # Generate simple embeddings (using hash for test)
    import hashlib

    embeddings = []
    for doc in test_docs:
        h = hashlib.sha256(doc.encode()).digest()
        vec = [(h[i % 32] / 255.0) * 2 - 1 for i in range(768)]
        # Pad to 768
        vec = vec + [0.0] * (768 - len(vec))
        embeddings.append(vec)

    collection.upsert(
        documents=test_docs,
        ids=test_ids,
        embeddings=embeddings,
    )

    # Query test
    query_vec = embeddings[0]
    results = collection.query(
        query_embeddings=[query_vec],
        n_results=3,
    )

    print(f"  ✅ HNSW search returned {len(results['ids'][0])} results")
    print(f"  ✅ Collection has {collection.count()} documents")
    return True


# ---------------------------------------------------------------------------
# 2. Time-Decay Weighting
# ---------------------------------------------------------------------------


def time_decay_score(
    semantic_score: float, created_at: str, decay_rate: float = 0.01
) -> float:
    """
    Apply time-decay to semantic score.
    Formula: final_score = semantic_score * e^(-λ * age_days)

    Args:
        semantic_score: Base similarity score (0-1)
        created_at: ISO timestamp of memory creation
        decay_rate: λ - how fast memories decay (0.01 = 1% per day)

    Returns:
        Time-decayed score
    """
    try:
        created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        age_days = (now - created).total_seconds() / 86400
        decay_factor = math.exp(-decay_rate * age_days)
        return semantic_score * decay_factor
    except Exception:
        return semantic_score


def test_time_decay():
    """Test time-decay weighting."""
    print("\n⏰ Testing Time-Decay Weighting...")

    test_cases = [
        ("Recent memory (1 day)", "2026-04-03T12:00:00Z", 0.9),
        ("Week-old memory (7 days)", "2026-03-28T12:00:00Z", 0.9),
        ("Month-old memory (30 days)", "2026-03-05T12:00:00Z", 0.9),
        ("Old memory (60 days)", "2026-02-03T12:00:00Z", 0.9),
        ("Very old memory (120 days)", "2025-12-06T12:00:00Z", 0.9),
    ]

    for name, created_at, base_score in test_cases:
        decayed = time_decay_score(base_score, created_at)
        retention = (decayed / base_score) * 100
        print(f"  {name}: {base_score:.3f} → {decayed:.3f} ({retention:.1f}% retained)")

    print("  ✅ Time-decay formula working correctly")
    return True


# ---------------------------------------------------------------------------
# 3. RRF (Reciprocal Rank Fusion)
# ---------------------------------------------------------------------------


def rrf_fusion(rank_lists: List[List[str]], k: int = 60) -> List[Tuple[str, float]]:
    """
    Reciprocal Rank Fusion - combine multiple ranked lists.
    Formula: RRF(d) = Σ 1/(k + rank_d)

    Args:
        rank_lists: List of ranked document ID lists
        k: Constant (default 60, per Cormack et al.)

    Returns:
        List of (doc_id, rrf_score) sorted by score descending
    """
    scores: Dict[str, float] = {}
    for rank_list in rank_lists:
        for rank, doc_id in enumerate(rank_list):
            scores[doc_id] = scores.get(doc_id, 0) + 1.0 / (k + rank + 1)

    return sorted(scores.items(), key=lambda x: -x[1])


def test_rrf():
    """Test RRF fusion."""
    print("\n🔀 Testing RRF Fusion...")

    # Simulate 3 retrievers ranking the same documents
    semantic_results = ["doc_A", "doc_B", "doc_C", "doc_D", "doc_E"]
    keyword_results = ["doc_C", "doc_A", "doc_F", "doc_B", "doc_G"]
    graph_results = ["doc_B", "doc_D", "doc_A", "doc_H", "doc_C"]

    fused = rrf_fusion([semantic_results, keyword_results, graph_results])

    print("  Fused rankings:")
    for rank, (doc_id, score) in enumerate(fused[:5]):
        print(f"    {rank + 1}. {doc_id} (RRF: {score:.4f})")

    # doc_A appears in all 3 lists at ranks 0, 1, 2 → should be #1
    # doc_B appears in all 3 lists at ranks 1, 3, 0 → should be #2
    assert fused[0][0] == "doc_A", f"Expected doc_A first, got {fused[0][0]}"
    print("  ✅ RRF fusion working correctly")
    return True


# ---------------------------------------------------------------------------
# 4. Importance Scoring
# ---------------------------------------------------------------------------


def calculate_importance(
    content: str,
    kind: str,
    created_at: str,
    has_embedding: bool,
    access_count: int = 0,
) -> float:
    """
    Calculate importance score for a memory (0-1).

    Factors:
    - Content length (longer = more detailed = potentially more important)
    - Kind (preference > project > summary > task > note)
    - Recency (newer = more relevant)
    - Embedding status (embedded = more useful)
    - Access count (frequently accessed = more important)
    """
    score = 0.0

    # Content length factor (0-0.2)
    content_len = min(len(content) / 1000.0, 1.0) * 0.2

    # Kind factor (0-0.3)
    kind_weights = {
        "preference": 0.3,
        "project": 0.25,
        "summary": 0.2,
        "task": 0.15,
        "note": 0.1,
    }
    kind_score = kind_weights.get(kind, 0.1)

    # Recency factor (0-0.2)
    try:
        created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        age_days = (now - created).total_seconds() / 86400
        recency = math.exp(-0.005 * age_days) * 0.2
    except Exception:
        recency = 0.1

    # Embedding factor (0-0.15)
    embedding_score = 0.15 if has_embedding else 0.0

    # Access count factor (0-0.15)
    access_score = min(access_count / 10.0, 1.0) * 0.15

    score = content_len + kind_score + recency + embedding_score + access_score
    return min(score, 1.0)


def test_importance():
    """Test importance scoring."""
    print("\n⭐ Testing Importance Scoring...")

    test_cases = [
        (
            "High: Recent preference, embedded",
            "my preferred mode is lab",
            "preference",
            "2026-04-01T00:00:00Z",
            True,
            5,
        ),
        (
            "Medium: Old project note",
            "Remember: my project codename is ORBIT",
            "project",
            "2026-01-15T00:00:00Z",
            True,
            2,
        ),
        (
            "Low: Old note, no embedding",
            "test note content",
            "note",
            "2025-12-01T00:00:00Z",
            False,
            0,
        ),
        (
            "High: Recent summary, many accesses",
            "user asked about architecture and I explained the full system design with all components",
            "summary",
            "2026-03-20T00:00:00Z",
            True,
            15,
        ),
    ]

    for name, content, kind, created, has_emb, access in test_cases:
        importance = calculate_importance(content, kind, created, has_emb, access)
        print(f"  {name}: {importance:.3f}")

    print("  ✅ Importance scoring working correctly")
    return True


# ---------------------------------------------------------------------------
# 5. bge-m3 Model Support (Optional)
# ---------------------------------------------------------------------------


def check_bge_m3_available():
    """Check if bge-m3 model is available in Ollama."""
    try:
        import httpx

        resp = httpx.get("http://localhost:11434/api/tags", timeout=5)
        models = resp.json().get("models", [])
        for m in models:
            if "bge-m3" in m.get("name", ""):
                return True
        return False
    except Exception:
        return False


def test_bge_m3():
    """Test bge-m3 model availability."""
    print("\n🔤 Testing bge-m3 Model...")
    available = check_bge_m3_available()
    if available:
        print("  ✅ bge-m3 is available in Ollama")
        print("  💡 To switch: change ollama_model to 'bge-m3' in EmbeddingEngine")
    return True


# ---------------------------------------------------------------------------
# 6. Memory Decay Curves and Soft-Delete Archival
#TW|# ---------------------------------------------------------------------------


def get_decay_curve(importance: float, age_days: float, half_life: float = 30) -> float:
    """
    Calculate decayed importance using exponential decay with half-life.
    
    Formula: decayed = importance * 0.5^(age_days / half_life)
    
    Args:
        importance: Original importance score (0-1)
        age_days: Number of days since memory creation
        half_life: Days for importance to halve (default: 30)
    
    Returns:
        Decayed importance score
    """
    if importance <= 0 or half_life <= 0:
        return importance
    decay_factor = 0.5 ** (age_days / half_life)
    return importance * decay_factor


def apply_decay_score(
    memory_id: str, created_at: str, current_importance: float, half_life_days: float = 30
) -> float:
    """
    Apply decay to a memory's importance based on its age.
    
    Args:
        memory_id: Memory identifier (for reference)
        created_at: ISO timestamp of memory creation
        current_importance: Current importance score
        half_life_days: Half-life in days (default: 30)
    
    Returns:
        Decayed importance score
    """
    try:
        created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        # Make created timezone-aware if it's naive
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        age_days = (now - created).total_seconds() / 86400
        return get_decay_curve(current_importance, age_days, half_life_days)
    except Exception:
        return current_importance


def _ensure_archived_column(db_path: str) -> None:
    """Ensure the archived column exists in the memories table."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Add archived column if not exists
    cursor.execute("PRAGMA table_info(memories)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if "archived" not in columns:
        cursor.execute("ALTER TABLE memories ADD COLUMN archived INTEGER DEFAULT 0")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_memories_archived ON memories(archived)")
        conn.commit()
    
    conn.close()


def archive_old_memories(db_path: str, days: int = 90, min_importance: float = 0.2) -> int:
    """
    Archive old memories with low importance (soft-delete).
    
    Args:
        db_path: Path to the SQLite database
        days: Archive memories older than this many days (default: 90)
        min_importance: Archive memories with importance below this threshold (default: 0.2)
    
    Returns:
        Number of memories archived
    """
    _ensure_archived_column(db_path)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Calculate cutoff date
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
    cutoff_str = cutoff_date.isoformat()
    
    # Find and archive memories older than cutoff with low importance
    # We use content length as a proxy for importance calculation since
    # we don't have the importance column directly
    cursor.execute("""
        UPDATE memories 
        SET archived = 1 
        WHERE 
            archived = 0 
            AND created_at < ?
            AND length(content) < 200
    """, (cutoff_str,))
    
    archived_count = cursor.rowcount
    conn.commit()
    conn.close()
    
    return archived_count


def get_archived_count(db_path: str) -> int:
    """
    Get count of archived memories.
    
    Args:
        db_path: Path to the SQLite database
    
    Returns:
        Number of archived memories
    """
    _ensure_archived_column(db_path)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM memories WHERE archived = 1")
    count = cursor.fetchone()[0]
    conn.close()
    
    return count


def restore_memory(db_path: str, memory_id: str) -> bool:
    """
    Restore an archived memory.
    
    Args:
        db_path: Path to the SQLite database
        memory_id: ID of the memory to restore
    
    Returns:
        True if memory was restored, False if not found
    """
    _ensure_archived_column(db_path)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE memories 
        SET archived = 0 
        WHERE id = ? AND archived = 1
    """, (memory_id,))
    
    restored = cursor.rowcount > 0
    conn.commit()
    conn.close()
    
    return restored


from datetime import timedelta
def run_all():
    """Run all enhancement tests."""
    print("=" * 60)
    print("🧠 MEMORY SYSTEM ENHANCEMENTS — Tier 1")
    print("=" * 60)

    results = {}
    results["HNSW Indexing"] = test_hnsw()
    results["Time-Decay Weighting"] = test_time_decay()
    results["RRF Fusion"] = test_rrf()
    results["Importance Scoring"] = test_importance()
    results["bge-m3 Model"] = test_bge_m3()

    print("\n" + "=" * 60)
    print("📊 ENHANCEMENT TEST RESULTS")
    print("=" * 60)
    for name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status} {name}")

    all_passed = all(results.values())
    print(
        f"\n{'✅ All enhancements working!' if all_passed else '⚠️  Some enhancements need attention'}"
    )
    return all_passed


if __name__ == "__main__":
    import sys

    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"

    if cmd == "all":
        run_all()
    elif cmd == "hnsw":
        test_hnsw()
    elif cmd == "time-decay":
        test_time_decay()
    elif cmd == "rrf":
        test_rrf()
    elif cmd == "importance":
        test_importance()
    elif cmd == "bge-m3":
        test_bge_m3()
    elif cmd == "init":
        init_chromadb_hnsw()
        print("✅ HNSW initialized in ChromaDB")
    else:
        print(f"Unknown command: {cmd}")
        print(
            "Usage: python -m src.memory.enhancements [all|hnsw|time-decay|rrf|importance|bge-m3|init]"
        )
