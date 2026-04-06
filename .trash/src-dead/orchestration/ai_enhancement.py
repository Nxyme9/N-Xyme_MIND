"""
AI Enhancement Service — Ported from N-Xyme MIND

Provides AI-powered features for various panels:
- Memory summary generation
- Memory tag suggestions
- Semantic memory search
- File organization suggestions
- Code review

Usage:
    service = AIEnhancementService()
    summary = service.generate_memory_summary(facts)
    tags = service.suggest_memory_tags("Working on RAG service")
"""

import logging
import os
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class AIEnhancementService:
    """AI-powered panel enhancements."""

    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        default_model: str = "llama3.2:3b",
    ):
        self.ollama_url = ollama_url
        self.default_model = default_model
        self._http_client = None
        self._cache: Dict[str, Any] = {}
        self._cache_ttl = 300  # 5 minutes

    def _get_client(self) -> httpx.Client:
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.Client(timeout=30.0)
        return self._http_client

    def _call_ai(self, prompt: str, model: Optional[str] = None) -> str:
        """Call Ollama for AI generation."""
        model = model or self.default_model

        # Check cache
        cache_key = f"{model}:{prompt[:100]}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            client = self._get_client()
            resp = client.post(
                f"{self.ollama_url}/api/generate",
                json={"model": model, "prompt": prompt, "stream": False},
                timeout=30,
            )
            resp.raise_for_status()
            result = resp.json().get("response", "")

            # Cache result
            self._cache[cache_key] = result
            return result
        except Exception as e:
            logger.error(f"AI Enhancement: Call failed: {e}")
            return ""

    # ============ Memory Panel ============

    def generate_memory_summary(self, facts: List[Dict]) -> str:
        """Generate AI summary of memory facts."""
        if not facts:
            return "No memories to summarize."

        facts_text = "\n".join([f.get("fact_text", f.get("text", "")) for f in facts[:10]])
        prompt = f"Summarize these memories in 2-3 sentences:\n{facts_text}\n\nSummary:"
        return self._call_ai(prompt)

    def suggest_memory_tags(self, fact_text: str) -> List[str]:
        """Suggest tags for a memory fact."""
        prompt = f"Suggest 3-5 relevant tags for this memory. Return only tags, comma-separated:\n{fact_text}\n\nTags:"
        result = self._call_ai(prompt)
        if result:
            return [t.strip() for t in result.split(",") if t.strip()]
        return []

    def semantic_search_memory(self, query: str, facts: List[Dict]) -> List[Dict]:
        """AI-powered semantic search over memories."""
        if not facts:
            return []

        query_lower = query.lower()
        results = []

        for fact in facts:
            fact_text = fact.get("fact_text", fact.get("text", "")).lower()

            # Direct match
            if query_lower in fact_text:
                results.append({**fact, "relevance": 1.0})
                continue

            # AI semantic match (only if Ollama available)
            prompt = f"On a scale of 0-1, how relevant is this memory to the query?\nQuery: {query}\nMemory: {fact.get('fact_text', fact.get('text', ''))}\n\nRelevance (0-1):"
            result = self._call_ai(prompt)
            try:
                relevance = float(result.strip()) if result.strip() else 0
                if relevance > 0.5:
                    results.append({**fact, "relevance": relevance})
            except (ValueError, TypeError):
                pass

        return sorted(results, key=lambda x: x.get("relevance", 0), reverse=True)[:10]

    # ============ Files Panel ============

    def suggest_file_organization(self, files: List[Dict]) -> List[Dict[str, str]]:
        """Suggest file organization based on content."""
        if not files:
            return []

        file_names = [f.get("name", "") for f in files[:20]]
        prompt = f"Suggest folder organization for these files. Group related files together.\nFiles: {', '.join(file_names)}\n\nProvide organization as JSON array of {{folder: name, files: [list of files]}}:"
        result = self._call_ai(prompt)
        try:
            import json

            return json.loads(result)
        except (json.JSONDecodeError, TypeError):
            return []

    # ============ Code Panel ============

    def review_code(self, code: str, language: str = "python") -> Dict[str, Any]:
        """AI code review."""
        prompt = f"Review this {language} code for issues. Return JSON with 'issues' (list), 'suggestions' (list), 'score' (0-100):\n\n{code[:1000]}\n\nReview:"
        result = self._call_ai(prompt)
        try:
            import json

            return json.loads(result)
        except (json.JSONDecodeError, TypeError):
            return {"issues": [], "suggestions": [], "score": 50}

    def suggest_code_improvements(self, code: str, language: str = "python") -> List[str]:
        """Suggest code improvements."""
        prompt = f"Suggest 3 improvements for this {language} code. Return as bullet points:\n\n{code[:500]}\n\nSuggestions:"
        result = self._call_ai(prompt)
        if result:
            return [s.strip().lstrip("- ") for s in result.split("\n") if s.strip()]
        return []

    # ============ Terminal Panel ============

    def suggest_command(self, context: str) -> str:
        """Suggest terminal command based on context."""
        prompt = f"Suggest a terminal command for: {context}\n\nCommand:"
        return self._call_ai(prompt).strip()

    # ============ Git Panel ============

    def suggest_commit_message(self, changes: str) -> str:
        """Suggest commit message based on changes."""
        prompt = f"Suggest a concise commit message for these changes:\n\n{changes[:500]}\n\nCommit message:"
        return self._call_ai(prompt).strip()

    def close(self):
        if self._http_client and not self._http_client.is_closed:
            self._http_client.close()


def create_catalyst_ai_enhancement() -> AIEnhancementService:
    """Create AI enhancement service for Catalyst."""
    return AIEnhancementService(
        ollama_url="http://localhost:11434",
        default_model="llama3.2:3b",
    )
