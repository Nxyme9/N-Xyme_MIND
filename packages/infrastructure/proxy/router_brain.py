"""Local LLM Router Brain — Analyzes requests for intelligent routing decisions."""

import time
import json
import threading
from typing import Dict, List, Optional

# Model capability matrix (pre-computed benchmarks)
MODEL_CAPABILITIES = {
    "qwen3.6-plus": {"reasoning": 0.95, "coding": 0.92, "creative": 0.88, "math": 0.90, "analysis": 0.93, "summarization": 0.90, "context_window": 131072, "cost_per_1m": 0.0},
    "qwen3-coder": {"reasoning": 0.85, "coding": 0.97, "creative": 0.75, "math": 0.80, "analysis": 0.82, "summarization": 0.78, "context_window": 131072, "cost_per_1m": 0.0},
    "nemotron-30b": {"reasoning": 0.78, "coding": 0.72, "creative": 0.80, "math": 0.75, "analysis": 0.80, "summarization": 0.82, "context_window": 32768, "cost_per_1m": 0.0},
    "nemotron-12b": {"reasoning": 0.70, "coding": 0.65, "creative": 0.75, "math": 0.68, "analysis": 0.72, "summarization": 0.78, "context_window": 32768, "cost_per_1m": 0.0},
    "minimax-m2.5": {"reasoning": 0.72, "coding": 0.70, "creative": 0.78, "math": 0.70, "analysis": 0.75, "summarization": 0.80, "context_window": 32768, "cost_per_1m": 0.0},
    "deepseek-r1": {"reasoning": 0.93, "coding": 0.88, "creative": 0.82, "math": 0.91, "analysis": 0.90, "summarization": 0.85, "context_window": 131072, "cost_per_1m": 0.0},
    "gemini-2.5-flash": {"reasoning": 0.82, "coding": 0.78, "creative": 0.85, "math": 0.80, "analysis": 0.85, "summarization": 0.88, "context_window": 1048576, "cost_per_1m": 0.0},
}

# Keyword-based category detection (fast, no LLM needed)
CATEGORY_KEYWORDS = {
    "coding": ["code", "function", "class", "def ", "async ", "implement", "debug", "fix bug", "refactor", "api", "endpoint", "database", "sql", "test", "unit test", "bug", "error", "exception"],
    "reasoning": ["why", "how does", "explain", "analyze", "compare", "evaluate", "architecture", "design", "reason", "think", "logic", "implications", "trade-offs"],
    "creative": ["write", "story", "poem", "creative", "imagine", "generate", "compose", "draft", "narrative"],
    "math": ["calculate", "equation", "formula", "math", "solve", "integral", "derivative", "probability", "statistics"],
    "summarization": ["summarize", "summary", "brief", "tl;dr", "key points", "overview", "condense"],
    "analysis": ["analyze", "review", "critique", "evaluate", "assess", "audit", "inspect", "security", "vulnerability"],
}


class RouterBrain:
    """Analyzes requests and selects optimal model."""

    def __init__(self, use_llm: bool = False, ollama_url: str = "http://localhost:11434", model: str = "llama3.2:3b"):
        self._cache: Dict[str, dict] = {}
        self._lock = threading.Lock()
        self.use_llm = use_llm
        self.ollama_url = ollama_url
        self.model = model
        self._llm_cache: Dict[str, dict] = {}

    def analyze_request(self, prompt: str, system_prompt: str = "", agent_type: str = "") -> dict:
        """Analyze request and return routing decision."""
        cache_key = hash(f"{prompt[:200]}:{agent_type}")
        with self._lock:
            if cache_key in self._cache:
                return self._cache[cache_key]

        start = time.time()

        # Use LLM analysis if enabled and available
        if self.use_llm:
            analysis = self._analyze_with_llm(prompt, system_prompt, agent_type)
        else:
            analysis = self._analyze_with_keywords(prompt, system_prompt, agent_type)

        analysis["analysis_time_ms"] = round((time.time() - start) * 1000, 1)

        with self._lock:
            self._cache[cache_key] = analysis
        return analysis

    def _analyze_with_keywords(self, prompt: str, system_prompt: str = "", agent_type: str = "") -> dict:
        """Fast keyword-based analysis."""
        text = (prompt + " " + system_prompt).lower()

        # Agent-based hints
        agent_hints = {
            "hephaestus": {"coding": 0.9},
            "oracle": {"analysis": 0.9, "reasoning": 0.8},
            "explore": {"analysis": 0.7},
            "librarian": {"summarization": 0.8, "analysis": 0.7},
            "sisyphus": {"reasoning": 0.7, "analysis": 0.6},
            "prometheus": {"reasoning": 0.8, "analysis": 0.7},
            "momus": {"analysis": 0.9, "reasoning": 0.7},
        }

        categories = self._detect_categories(prompt)
        complexity = self._estimate_complexity(prompt, system_prompt)
        required_caps = self._get_required_capabilities(categories)

        # Apply agent hints
        if agent_type in agent_hints:
            for cap, weight in agent_hints[agent_type].items():
                required_caps[cap] = max(required_caps.get(cap, 0), weight)

        model_scores = self._score_models(required_caps, complexity)
        best_model = max(model_scores, key=lambda m: m["score"])

        return {
            "categories": categories, "complexity": complexity,
            "required_capabilities": required_caps,
            "best_model": best_model["model"], "best_score": round(best_model["score"], 3),
            "model_scores": {m["model"]: round(m["score"], 3) for m in sorted(model_scores, key=lambda m: m["score"], reverse=True)[:3]},
        }

    def _analyze_with_llm(self, prompt: str, system_prompt: str = "", agent_type: str = "") -> dict:
        """LLM-based analysis for more accurate routing."""
        cache_key = hash(f"llm:{prompt[:200]}:{agent_type}")
        with self._lock:
            if cache_key in self._llm_cache:
                return self._llm_cache[cache_key]

        try:
            import urllib.request
            url = f"{self.ollama_url}/api/generate"
            payload = {
                "model": self.model,
                "prompt": f"""Analyze this request and return ONLY valid JSON:
{{"categories": ["coding"/"reasoning"/"creative"/"math"/"summarization"/"analysis"], "complexity": "simple"/"medium"/"complex", "required_capabilities": {{"reasoning": 0-1, "coding": 0-1, "creative": 0-1, "math": 0-1, "analysis": 0-1, "summarization": 0-1}}}}

Request: {prompt[:500]}
Agent: {agent_type}""",
                "stream": False,
                "options": {"temperature": 0.1, "num_predict": 200},
            }
            req = urllib.request.Request(url, json=payload, headers={"Content-Type": "application/json"})
            resp = urllib.request.urlopen(req, timeout=5)
            data = json.loads(resp.read())
            response = data.get("response", "{}")
            import re
            match = re.search(r'\{[^}]+\}', response)
            if match:
                result = json.loads(match.group())
                with self._lock:
                    self._llm_cache[cache_key] = result
                return result
        except Exception:
            pass

        # Fallback to keyword analysis
        return self._analyze_with_keywords(prompt, system_prompt, agent_type)

    def _detect_categories(self, prompt: str) -> List[str]:
        prompt_lower = prompt.lower()
        detected = [cat for cat, kws in CATEGORY_KEYWORDS.items() if any(kw in prompt_lower for kw in kws)]
        return detected if detected else ["general"]

    def _estimate_complexity(self, prompt: str, system_prompt: str = "") -> str:
        text = (prompt + " " + system_prompt).lower()
        length = len(text)
        if length < 100: base = "simple"
        elif length < 500: base = "medium"
        else: base = "complex"
        complex_kws = ["architecture", "design pattern", "distributed", "microservice", "optimize", "refactor", "implement from scratch"]
        simple_kws = ["what is", "define", "list", "show me", "explain briefly", "simple", "basic"]
        if any(kw in text for kw in complex_kws): return "complex"
        if any(kw in text for kw in simple_kws): return "simple"
        return base

    def _get_required_capabilities(self, categories: List[str]) -> Dict[str, float]:
        caps = {"reasoning": 0.5, "coding": 0.5, "creative": 0.5, "math": 0.5, "analysis": 0.5, "summarization": 0.5}
        weights = {
            "coding": {"coding": 0.9, "reasoning": 0.6}, "reasoning": {"reasoning": 0.9, "analysis": 0.7},
            "creative": {"creative": 0.9}, "math": {"math": 0.9, "reasoning": 0.6},
            "summarization": {"summarization": 0.9}, "analysis": {"analysis": 0.9, "reasoning": 0.6},
        }
        for cat in categories:
            if cat in weights:
                for cap, w in weights[cat].items():
                    caps[cap] = max(caps[cap], w)
        return caps

    def _score_models(self, required_caps: Dict[str, float], complexity: str) -> List[dict]:
        scores = []
        for model_name, caps in MODEL_CAPABILITIES.items():
            cap_score = sum(caps.get(cap, 0) * w for cap, w in required_caps.items())
            cap_score /= sum(required_caps.values()) if required_caps else 1
            complexity_bonus = {"simple": 0.0, "medium": 0.05, "complex": 0.1}.get(complexity, 0.0)
            context_penalty = -0.2 if caps["context_window"] < 8192 else 0.0
            scores.append({"model": model_name, "score": max(0.0, cap_score + complexity_bonus + context_penalty)})
        return scores


# Global instance - keyword-based by default (fast), set use_llm=True for LLM analysis
router_brain = RouterBrain(use_llm=False)
