"""
Reflexion Pattern — Self-improving agents with external research

Implements the Reflexion pattern: Draft → Self-Critique → Research → Revise

Usage:
    reflexion = ReflexionAgent()
    result = reflexion.execute(task, max_iterations=3)
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


@dataclass
class ReflexionIteration:
    """A single iteration of the Reflexion loop."""

    iteration: int
    draft: str
    critique: str
    research_queries: List[str]
    research_results: List[str]
    revision: str
    confidence: float
    timestamp: float = field(default_factory=time.time)


@dataclass
class ReflexionResult:
    """Final result of Reflexion execution."""

    task: str
    final_output: str
    iterations: int
    confidence: float
    history: List[ReflexionIteration]
    improved: bool


class ReflexionAgent:
    """
    Self-improving agent using Reflexion pattern.

    Pattern:
    1. Draft initial response
    2. Self-critique (find flaws)
    3. Generate search queries for missing info
    4. Research (external tools)
    5. Revise using evidence
    6. Repeat until confident
    """

    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        model: str = "llama3.2:3b-instruct-q4_K_M",
    ):
        self.ollama_url = ollama_url
        self.model = model
        self._client = None
        logger.info(f"ReflexionAgent: Initialized (model={model})")

    def _get_client(self) -> httpx.Client:
        if self._client is None or self._client.is_closed:
            self._http_client = httpx.Client(timeout=30.0)
        return self._http_client

    def execute(
        self,
        task: str,
        max_iterations: int = 3,
        confidence_threshold: float = 0.8,
    ) -> ReflexionResult:
        """Execute task with Reflexion self-improvement."""
        history = []
        current_output = ""
        confidence = 0.0

        for i in range(max_iterations):
            logger.info(f"Reflexion: Iteration {i + 1}/{max_iterations}")

            # Step 1: Draft
            if i == 0:
                draft = self._draft(task)
            else:
                draft = self._revise(task, current_output, history[-1])

            # Step 2: Self-critique
            critique = self._critique(task, draft)

            # Step 3: Generate research queries
            queries = self._generate_queries(critique)

            # Step 4: Research
            research = self._research(queries)

            # Step 5: Calculate confidence
            confidence = self._calculate_confidence(draft, critique, research)

            # Record iteration
            iteration = ReflexionIteration(
                iteration=i + 1,
                draft=draft,
                critique=critique,
                research_queries=queries,
                research_results=research,
                revision=draft if i == 0 else current_output,
                confidence=confidence,
            )
            history.append(iteration)

            current_output = draft

            # Step 6: Check if confident enough
            if confidence >= confidence_threshold:
                logger.info(
                    f"Reflexion: Confidence {confidence:.2f} >= {confidence_threshold}, stopping"
                )
                break

        improved = len(history) > 1 and history[-1].confidence > history[0].confidence

        return ReflexionResult(
            task=task,
            final_output=current_output,
            iterations=len(history),
            confidence=confidence,
            history=history,
            improved=improved,
        )

    def _draft(self, task: str) -> str:
        """Generate initial draft."""
        prompt = f"Task: {task}\n\nProvide a detailed response:"
        return self._call_llm(prompt)

    def _critique(self, task: str, draft: str) -> str:
        """Self-critique the draft."""
        prompt = f"""Task: {task}

Draft response:
{draft}

Critique this response. What's missing? What's wrong? What could be better?

Critique:"""
        return self._call_llm(prompt)

    def _generate_queries(self, critique: str) -> List[str]:
        """Generate research queries based on critique."""
        prompt = f"""Based on this critique, generate 2-3 specific search queries to find missing information:

{critique}

Queries (one per line):"""
        result = self._call_llm(prompt)
        return [q.strip() for q in result.split("\n") if q.strip()][:3]

    def _research(self, queries: List[str]) -> List[str]:
        """Research using external tools (simulated)."""
        results = []
        for query in queries:
            # In a real implementation, this would call search tools
            results.append(f"Research result for: {query}")
        return results

    def _revise(self, task: str, draft: str, iteration: ReflexionIteration) -> str:
        """Revise draft using research evidence."""
        prompt = f"""Task: {task}

Original draft:
{draft}

Critique:
{iteration.critique}

Research findings:
{chr(10).join(iteration.research_results)}

Revise the draft to address the critique and incorporate the research:"""
        return self._call_llm(prompt)

    def _calculate_confidence(self, draft: str, critique: str, research: List[str]) -> float:
        """Calculate confidence score."""
        # Simple heuristic: fewer critique issues = higher confidence
        critique_words = len(critique.split())
        if critique_words < 20:
            return 0.9
        elif critique_words < 50:
            return 0.7
        else:
            return 0.5

    def _call_llm(self, prompt: str) -> str:
        """Call Ollama for generation."""
        try:
            client = self._get_client()
            resp = client.post(
                f"{self.ollama_url}/api/generate",
                json={"model": self.model, "prompt": prompt, "stream": False},
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json().get("response", "")
        except Exception as e:
            logger.error(f"ReflexionAgent: LLM call failed: {e}")
            return ""

    def close(self):
        if self._client and not self._client.is_closed:
            self._client.close()
