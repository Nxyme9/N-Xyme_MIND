"""Memory tab - memory system status."""


def get_content(live_data: dict) -> str:
    mem_sources = live_data.get("memory_sources", 0)
    mem_enabled = live_data.get("memory_enabled", 0)
    idx_files = live_data.get("indexed_files", 0)
    idx_chunks = live_data.get("indexed_chunks", 0)

    lrn_feedback = live_data.get("learning_feedback", 0)
    lrn_queries = live_data.get("learning_queries", 0)

    return f"""MEMORY SYSTEM

Sources
  Total: {mem_sources} | Enabled: {mem_enabled}

File Index
  Files: {idx_files} | Chunks: {idx_chunks}

Learning
  Feedback: {lrn_feedback}
  Queries: {lrn_queries}"""
