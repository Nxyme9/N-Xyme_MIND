from typing import Any

from athena.memory.vectors import get_client, get_embedding

# Supported embedding dimensions per model (multi-model support)
EXPECTED_DIMS = {
    "gemini-embedding-001": 3072,
    "nomic-embed-text": 768,
    "mxbai-embed-large": 1024,
}


class HealthCheck:
    """Core health monitoring for Athena services."""

    @staticmethod
    def check_vector_api() -> dict[str, Any]:
        """Check embedding API responsiveness across supported models.

        Reads embedding dimensions from the actual embedding, then matches
        against known models. Returns the detected model name on success.
        """
        try:
            test_text = "health check"
            embedding = get_embedding(test_text)
            dims = len(embedding)
            # Determine which model produced these dims, if any
            detected_model = None
            for model_name, expected in EXPECTED_DIMS.items():
                if dims == expected:
                    detected_model = model_name
                    break
            if detected_model:
                return {"status": "PASS", "dims": dims, "model": detected_model}
            else:
                return {
                    "status": "FAIL",
                    "error": f"Unknown embedding dimensions: {dims}",
                }
        except Exception as e:
            return {"status": "FAIL", "error": str(e)}

    @staticmethod
    def check_database() -> dict[str, Any]:
        """Check database health.

        If EMBEDDING_PROVIDER=ollama, use local ChromaDB at the expected path.
        Otherwise, fall back to the existing Supabase health check.
        """
        try:
            chroma_path = "./athena/.agent/chroma_db"
            import os
            provider = (os.environ.get("EMBEDDING_PROVIDER", "").lower() or
                       ("ollama" if os.path.exists(chroma_path) else ""))

            if provider == "ollama" or os.path.exists(chroma_path):
                # Use local ChromaDB instead of Supabase when using Ollama embeddings
                chroma_path = "./athena/.agent/chroma_db"
                try:
                    import chromadb
                    client = chromadb.PersistentClient(path=chroma_path)

                    # Count collections to indicate health
                    try:
                        collections = client.list_collections()
                        count = len(collections) if collections is not None else 0
                        return {"status": "PASS", "record_count": count}
                    except Exception as exc3:
                        return {
                            "status": "FAIL",
                            "error": f"Failed to read ChromaDB collections: {exc3}",
                        }
                except Exception as e:
                    return {"status": "FAIL", "error": str(e)}
            # Default: Supabase health check path
            client = get_client()
            # Test a lightweight RPC or query
            # Checking sessions table count as a proxy for connectivity
            response = (
                client.table("sessions")
                .select("count", count="exact")
                .limit(1)
                .execute()
            )
            count = response.count if hasattr(response, "count") else 0
            return {"status": "PASS", "record_count": count}
        except Exception as e:
            return {"status": "FAIL", "error": str(e)}

    @classmethod
    def run_all(cls) -> bool:
        """Run all critical health checks and print results."""
        print("\n🔍 SYSTEM HEALTH AUDIT")
        print("─" * 30)

        vector = cls.check_vector_api()
        v_status = (
            f"✅ {vector['model']} ({vector['dims']}d)"
            if vector["status"] == "PASS"
            else f"❌ {vector.get('error')}"
        )
        print(f"   Vectors:  {v_status}")

        db = cls.check_database()
        db_status = (
            f"✅ Connected ({db['record_count']} records)"
            if db["status"] == "PASS"
            else f"❌ {db.get('error')}"
        )
        print(f"   Database: {db_status}")

        print("─" * 30)
        return vector["status"] == "PASS" and db["status"] == "PASS"


if __name__ == "__main__":
    # Internal test
    HealthCheck.run_all()
