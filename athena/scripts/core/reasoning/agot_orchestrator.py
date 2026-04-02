#!/usr/bin/env python3
"""
AGoT Orchestrator v5.0
Adaptive Graph of Thoughts implementation for Athena.

Protocol 75 v5.0 — AGoT-Enhanced Parallel Reasoning.
Upgrades static 4-track parallel reasoning to dynamic graph-based topology.

Based on:
  - Pandey et al. (2025), "Adaptive Graph of Thoughts", arXiv:2502.05078
  - Liu et al. (2026), "RouteGoT", arXiv:2603.05818
  - Besta et al. (2024), "Graph of Thoughts", arXiv:2308.09687

Key design decisions:
  1. Controller is deterministic Python, not LLM (meta-reasoning in code)
  2. BFS across layers, DFS into recursive sub-graphs
  3. Heritage-based node addressing for unique identification
  4. Progressive context summarization for context window management
  5. Async execution with semaphore-bounded concurrency
"""

from __future__ import annotations

import asyncio
import argparse
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path

# Add src to path
src_path = (Path(__file__).parent.parent.parent.parent / "src").resolve()
sys.path.insert(0, str(src_path))

from dotenv import load_dotenv  # noqa: E402
import google.generativeai as genai  # noqa: E402

load_dotenv()

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_MODEL = "gemini-2.5-flash"
MAX_OUTPUT_TOKENS = 8192

# AGoT configuration presets by complexity tier
AGOT_PRESETS = {
    "lite": {  # Λ 21-40
        "max_depth": 0,
        "max_layers": 2,
        "max_new_tasks": 3,
        "max_concurrent": 10,
        "confidence_threshold": 7.0,
        "use_tracks": False,
    },
    "full": {  # Λ 41-60
        "max_depth": 1,
        "max_layers": 3,
        "max_new_tasks": 4,
        "max_concurrent": 10,
        "confidence_threshold": 7.0,
        "use_tracks": False,
    },
    "tracks": {  # Λ > 60
        "max_depth": 2,
        "max_layers": 4,
        "max_new_tasks": 5,
        "max_concurrent": 10,
        "confidence_threshold": 7.0,
        "use_tracks": True,
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# Data Structures
# ─────────────────────────────────────────────────────────────────────────────


class NodeStatus(Enum):
    """Lifecycle state of a thought node."""

    PENDING = "pending"
    RESOLVING = "resolving"
    RESOLVED = "resolved"
    COMPLEX = "complex"  # Flagged for recursive decomposition
    TERMINATED = "terminated"  # Pruned (low confidence)


@dataclass
class ThoughtNode:
    """Single node in the AGoT reasoning graph."""

    node_id: str  # Heritage-based: "0-0", "1-2", etc.
    layer: int
    position: int
    heritage: tuple  # Full path for nested graphs
    subproblem: str
    result: str | None = None
    confidence: float = 0.0
    status: NodeStatus = NodeStatus.PENDING
    children: list[str] = field(default_factory=list)
    parents: list[str] = field(default_factory=list)
    nested_graph_summary: str | None = None  # Summary of recursive sub-graph
    latency_ms: int = 0
    persona: str | None = None  # Track persona (A/B/C/D) if applicable

    def is_alive(self) -> bool:
        return self.status not in (NodeStatus.TERMINATED,)


@dataclass
class AGoTGraph:
    """Full reasoning graph state."""

    query: str
    nodes: dict[str, ThoughtNode] = field(default_factory=dict)
    layers: dict[int, list[str]] = field(default_factory=dict)
    strategy_per_layer: dict[int, str] = field(default_factory=dict)
    depth: int = 0
    max_depth: int = 1
    max_layers: int = 3
    max_nodes_per_layer: int = 5

    def add_node(self, node: ThoughtNode):
        """Add a node to the graph."""
        self.nodes[node.node_id] = node
        if node.layer not in self.layers:
            self.layers[node.layer] = []
        self.layers[node.layer].append(node.node_id)

    def get_context_for_node(self, node: ThoughtNode, max_chars: int = 6000) -> str:
        """Get scoped context for a node — ancestors only, not siblings."""
        context_parts = []
        for layer_idx in range(node.layer):
            for nid in self.layers.get(layer_idx, []):
                n = self.nodes[nid]
                if n.result and n.is_alive():
                    entry = (
                        f"[Layer {layer_idx}, Node {n.position}] "
                        f"{n.subproblem[:100]}: {n.result[:300]}"
                    )
                    context_parts.append(entry)

        full = "\n".join(context_parts)
        # Truncate to prevent context overflow
        if len(full) > max_chars:
            full = full[:max_chars] + "\n[...context truncated...]"
        return full

    def get_resolved_leaves(self) -> list[ThoughtNode]:
        """Get all resolved leaf nodes (no children, status=RESOLVED)."""
        return [
            n
            for n in self.nodes.values()
            if n.status == NodeStatus.RESOLVED and not n.children
        ]

    def to_mermaid(self) -> str:
        """Export graph as Mermaid diagram for visualization."""
        lines = ["graph TD"]
        for nid, node in self.nodes.items():
            safe_id = nid.replace("-", "_")
            label = node.subproblem[:40].replace('"', "'")
            status_icon = {
                NodeStatus.RESOLVED: "✅",
                NodeStatus.TERMINATED: "❌",
                NodeStatus.COMPLEX: "🔄",
            }.get(node.status, "⏳")
            lines.append(f'    {safe_id}["{status_icon} {label}"]')
            for child_id in node.children:
                safe_child = child_id.replace("-", "_")
                lines.append(f"    {safe_id} --> {safe_child}")
        return "\n".join(lines)

    def get_metrics(self) -> dict:
        """Return graph metrics for reporting."""
        return {
            "total_nodes": len(self.nodes),
            "resolved_nodes": sum(
                1 for n in self.nodes.values() if n.status == NodeStatus.RESOLVED
            ),
            "terminated_nodes": sum(
                1 for n in self.nodes.values() if n.status == NodeStatus.TERMINATED
            ),
            "layers_used": len(self.layers),
            "max_depth_reached": self.depth,
        }


@dataclass
class AGoTResult:
    """Final output from AGoT reasoning."""

    synthesis: str
    graph_metadata: dict
    call_metrics: dict
    mermaid_diagram: str
    convergence_history: list[dict] = field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# Prompt Templates
# ─────────────────────────────────────────────────────────────────────────────

STRATEGY_PROMPT = """You are the STRATEGY ENGINE of an Adaptive Graph of Thoughts reasoning system.

Given the query and any context from prior layers, generate a decomposition strategy.

QUERY: {query}
CONTEXT FROM PRIOR LAYERS: {context}

Instructions:
1. Identify the key dimensions of this problem
2. Determine if it can be split into independent subproblems
3. Generate a brief strategy for decomposition (2-3 sentences)

Output your strategy as plain text (no JSON, no formatting)."""

DECOMPOSE_PROMPT = """You are the DECOMPOSITION ENGINE.

Given this query and strategy, break it into specific, independent subproblems.

QUERY: {query}
STRATEGY: {strategy}
MAX SUBPROBLEMS: {max_tasks}

Instructions:
1. Generate {max_tasks} or fewer specific subproblems
2. Each subproblem should be independently answerable
3. Together they should cover the full scope of the query

Output ONLY valid JSON:
{{"subproblems": ["subproblem 1", "subproblem 2", ...]}}"""

RESOLVE_PROMPT = """You are solving a specific subproblem as part of a larger reasoning chain.

ORIGINAL QUERY: {query}
YOUR ASSIGNED SUBPROBLEM: {subproblem}
CONTEXT FROM PRIOR REASONING: {context}
{persona_context}

Solve this subproblem thoroughly. Provide your complete answer.
At the end, rate your confidence in your answer (1-10).

Format:
ANSWER: [your detailed answer]
CONFIDENCE: [1-10]"""

COMPLEXITY_PROMPT = """Assess the complexity of this reasoning result.

SUBPROBLEM: {subproblem}
RESULT: {result}

Is this result fully resolved, or does it need further decomposition?
Consider: Does the answer require multiple independent sub-analyses?
Is there significant uncertainty that deeper investigation could resolve?

Output ONLY valid JSON:
{{"complexity": "SIMPLE" or "COMPLEX", "reason": "brief explanation"}}"""

SYNTHESIS_PROMPT = """You are the SYNTHESIS ENGINE of an Adaptive Graph of Thoughts system.

Multiple subproblems have been solved independently. Synthesize them into a final answer.

ORIGINAL QUERY: {query}

RESOLVED SUBPROBLEMS:
{resolved_nodes}

Instructions:
1. Integrate all subproblem results into a comprehensive answer
2. Resolve any contradictions between results
3. Ensure the synthesis addresses the original query completely
4. Rate your overall confidence (1-10)

Output format:
## Synthesis
[Your comprehensive synthesized answer]

## Confidence: [1-10]"""

# Track persona prompts (reused from parallel_orchestrator.py v4.0)
TRACK_PERSONAS = {
    "A_DOMAIN": "You are a DOMAIN EXPERT. Apply domain-specific frameworks and expertise. Ground analysis in real constraints.",
    "B_ADVERSARIAL": "You are an ADVERSARIAL SKEPTIC. Challenge every premise. Find flaws. Identify ruin vectors. Check Law #1 (No Irreversible Ruin).",
    "C_CROSS_DOMAIN": "You are a CROSS-DOMAIN PATTERN MATCHER. Abstract the problem. Find isomorphic patterns from unrelated fields.",
    "D_ZERO_POINT": "You are a ZERO-POINT FIRST PRINCIPLES thinker. Strip all assumptions. Apply inversion. Question the nature of the problem itself.",
}

CONVERGENCE_GATE_PROMPT = """You are the ADVERSARIAL CONVERGENCE GATE.

Score this synthesized analysis on four criteria (0-25 each):
- Logical Coherence: Is the reasoning valid?
- Risk Coverage: Are all major risks addressed?
- Actionability: Can someone act on this?
- Blind Spot Check: Are there obvious omissions?

SYNTHESIS TO SCORE:
{synthesis}

INTER-TRACK AGREEMENT LEVEL: {agreement_level}

Output ONLY valid JSON:
{{
    "logical_coherence": <0-25>,
    "risk_coverage": <0-25>,
    "actionability": <0-25>,
    "blind_spot_check": <0-25>,
    "total_score": <0-100>,
    "passed": <true/false>,
    "critique": "<one paragraph>",
    "suggestions": ["improvement 1", "improvement 2"]
}}"""


# ─────────────────────────────────────────────────────────────────────────────
# AGoT Controller
# ─────────────────────────────────────────────────────────────────────────────


class AGoTController:
    """
    Meta-controller for Adaptive Graph of Thoughts.

    The controller is deterministic Python logic — NOT another LLM call.
    It manages graph state, dispatches LLM calls, enforces limits,
    and decides graph operations based on node scores/status.
    """

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        preset: str = "full",
        verbose: bool = True,
    ):
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment")

        genai.configure(api_key=api_key)
        self.model_name = model
        self.verbose = verbose
        self.total_calls = 0
        self.total_latency_ms = 0

        # Load preset config
        config = AGOT_PRESETS.get(preset, AGOT_PRESETS["full"])
        self.max_depth = config["max_depth"]
        self.max_layers = config["max_layers"]
        self.max_new_tasks = config["max_new_tasks"]
        self.max_concurrent = config["max_concurrent"]
        self.confidence_threshold = config["confidence_threshold"]
        self.use_tracks = config["use_tracks"]
        self.preset_name = preset

    def _log(self, msg: str):
        if self.verbose:
            print(msg)

    async def _llm_call(
        self, prompt: str, temperature: float = 0.7, max_tokens: int = MAX_OUTPUT_TOKENS
    ) -> str:
        """Execute a single LLM call. All graph operations go through this."""
        start = time.time()
        self.total_calls += 1

        try:
            model = genai.GenerativeModel(
                model_name=self.model_name,
                generation_config=genai.GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                ),
            )

            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                None, lambda: model.generate_content(prompt)
            )

            latency = int((time.time() - start) * 1000)
            self.total_latency_ms += latency

            return response.text if response.text else "[No response]"

        except Exception as e:
            self._log(f"  ❌ LLM call failed: {e}")
            return f"[ERROR: {e}]"

    def _parse_json(self, text: str) -> dict:
        """Extract JSON from LLM response (handles markdown code blocks)."""
        text = text.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {}

    def _extract_confidence(self, text: str) -> float:
        """Extract confidence score from LLM response."""
        match = re.search(r"CONFIDENCE:\s*(\d+(?:\.\d+)?)", text)
        if match:
            return float(match.group(1))
        # Fallback: look for any number after "confidence"
        match = re.search(r"confidence[:\s]+(\d+(?:\.\d+)?)", text, re.IGNORECASE)
        if match:
            return float(match.group(1))
        return 5.0  # Default mid-range

    # ─────────────────── Graph Operations ───────────────────

    async def _generate_strategy(
        self, query: str, graph: AGoTGraph, layer: int, parent_context: str = ""
    ) -> str:
        """Phase 1: Generate decomposition strategy for this layer."""
        self._log(f"  📋 Generating strategy for layer {layer}...")

        context = parent_context or graph.get_context_for_node(
            ThoughtNode(
                node_id="tmp", layer=layer, position=0, heritage=(), subproblem=""
            )
        )

        prompt = STRATEGY_PROMPT.format(query=query, context=context or "(none)")
        return await self._llm_call(prompt, temperature=0.7, max_tokens=1024)

    async def _decompose(self, query: str, strategy: str, max_tasks: int) -> list[str]:
        """Phase 2: Decompose query into subproblems."""
        self._log(f"  🔀 Decomposing into ≤{max_tasks} subproblems...")

        prompt = DECOMPOSE_PROMPT.format(
            query=query, strategy=strategy, max_tasks=max_tasks
        )
        response = await self._llm_call(prompt, temperature=0.7, max_tokens=2048)
        parsed = self._parse_json(response)

        subproblems = parsed.get("subproblems", [])
        if not subproblems:
            # Fallback: treat entire query as single subproblem
            self._log("  ⚠️ Decomposition failed, using query as single node")
            subproblems = [query]

        return subproblems[:max_tasks]

    async def _resolve_node(
        self, node: ThoughtNode, graph: AGoTGraph, depth: int
    ) -> None:
        """Phase 3: Resolve a single node (potentially recursive)."""
        node.status = NodeStatus.RESOLVING
        context = graph.get_context_for_node(node)

        # Build persona context if applicable
        persona_ctx = ""
        if node.persona and node.persona in TRACK_PERSONAS:
            persona_ctx = f"PERSONA: {TRACK_PERSONAS[node.persona]}"

        prompt = RESOLVE_PROMPT.format(
            query=graph.query,
            subproblem=node.subproblem,
            context=context or "(none)",
            persona_context=persona_ctx,
        )

        start = time.time()
        result = await self._llm_call(prompt, temperature=0.8)
        node.latency_ms = int((time.time() - start) * 1000)
        node.result = result
        node.confidence = self._extract_confidence(result)

        # Assess complexity (should we recurse?)
        if depth < self.max_depth and node.confidence < self.confidence_threshold:
            complexity = await self._assess_complexity(node)

            if complexity == "COMPLEX":
                self._log(
                    f"    🔄 Node {node.node_id} flagged COMPLEX → "
                    f"spawning sub-graph (depth {depth + 1})"
                )
                node.status = NodeStatus.COMPLEX

                # Recursive AGoT solve
                sub_result = await self._solve_recursive(
                    node.subproblem, depth + 1, context
                )
                node.result = sub_result
                node.nested_graph_summary = sub_result[:200]
                node.confidence = self._extract_confidence(sub_result)

        node.status = NodeStatus.RESOLVED
        self._log(
            f"    ✅ Node {node.node_id}: "
            f"confidence={node.confidence:.1f} | {node.latency_ms}ms"
        )

    async def _assess_complexity(self, node: ThoughtNode) -> str:
        """Assess whether a node needs recursive decomposition."""
        prompt = COMPLEXITY_PROMPT.format(
            subproblem=node.subproblem,
            result=node.result[:1000] if node.result else "(no result)",
        )
        response = await self._llm_call(prompt, temperature=0.3, max_tokens=512)
        parsed = self._parse_json(response)
        return parsed.get("complexity", "SIMPLE")

    async def _synthesize(self, query: str, graph: AGoTGraph) -> str:
        """Phase 4: Synthesize all resolved nodes into final answer."""
        self._log("  🔗 Synthesizing resolved nodes...")

        resolved = graph.get_resolved_leaves()
        if not resolved:
            resolved = [n for n in graph.nodes.values() if n.result]

        node_texts = "\n\n".join(
            f"### Subproblem: {n.subproblem}\n"
            f"**Result** (confidence {n.confidence:.1f}/10):\n{n.result}"
            for n in resolved
        )

        prompt = SYNTHESIS_PROMPT.format(query=query, resolved_nodes=node_texts)
        return await self._llm_call(prompt, temperature=0.7)

    # ─────────────────── Main Entry Points ───────────────────

    async def _solve_recursive(
        self, query: str, depth: int = 0, parent_context: str = ""
    ) -> str:
        """Internal recursive solver — builds and resolves a single AGoT graph."""
        graph = AGoTGraph(
            query=query,
            depth=depth,
            max_depth=self.max_depth,
            max_layers=self.max_layers,
            max_nodes_per_layer=self.max_new_tasks,
        )

        current_layer = 0

        while current_layer < self.max_layers:
            # Phase 1: Strategy
            strategy = await self._generate_strategy(
                query, graph, current_layer, parent_context
            )
            graph.strategy_per_layer[current_layer] = strategy

            # Phase 2: Decompose (first layer) or plan next layer
            if current_layer == 0:
                subproblems = await self._decompose(query, strategy, self.max_new_tasks)
            else:
                # Subsequent layers: refine unresolved aspects
                unresolved = [
                    n
                    for n in graph.nodes.values()
                    if n.confidence < self.confidence_threshold and n.is_alive()
                ]
                if not unresolved:
                    break  # All nodes sufficiently confident
                subproblems = [
                    f"Further analyze and refine: {n.subproblem}"
                    for n in unresolved[: self.max_new_tasks]
                ]

            # Phase 3: Create and resolve nodes concurrently
            semaphore = asyncio.Semaphore(self.max_concurrent)
            tasks = []

            for i, sp in enumerate(subproblems):
                node = ThoughtNode(
                    node_id=f"{current_layer}-{i}",
                    layer=current_layer,
                    position=i,
                    heritage=(depth, current_layer, i),
                    subproblem=sp,
                )
                graph.add_node(node)

                async def resolve_bounded(n=node):
                    async with semaphore:
                        await self._resolve_node(n, graph, depth)

                tasks.append(resolve_bounded())

            await asyncio.gather(*tasks)

            # Check convergence
            layer_nodes = [
                graph.nodes[nid] for nid in graph.layers.get(current_layer, [])
            ]
            alive_nodes = [n for n in layer_nodes if n.is_alive()]
            if alive_nodes:
                avg_conf = sum(n.confidence for n in alive_nodes) / len(alive_nodes)
                if avg_conf >= self.confidence_threshold:
                    self._log(
                        f"  📊 Layer {current_layer} avg confidence "
                        f"{avg_conf:.1f} ≥ {self.confidence_threshold} → converged"
                    )
                    break

            current_layer += 1

        # Phase 4: Synthesize
        return await self._synthesize(query, graph)

    async def solve(self, query: str, context: str = "") -> AGoTResult:
        """
        Main public entry point.

        If use_tracks=True (Λ > 60), dispatches 4 track personas
        each with their own AGoT sub-graph, then synthesizes across tracks.
        """
        self._log("\n" + "=" * 60)
        self._log(f"🧠 AGOT ORCHESTRATOR v5.0 [{self.preset_name.upper()}]")
        self._log("=" * 60)
        self._log(f"Query: {query[:120]}...")
        self._log(
            f"Config: depth={self.max_depth}, layers={self.max_layers}, "
            f"tasks={self.max_new_tasks}, tracks={self.use_tracks}"
        )
        self._log("")

        start_time = time.time()

        if self.use_tracks:
            result = await self._solve_with_tracks(query, context)
        else:
            synthesis = await self._solve_recursive(
                query, depth=0, parent_context=context
            )

            # Build a basic graph for metrics (the recursive solver manages its own)
            result = AGoTResult(
                synthesis=synthesis,
                graph_metadata={
                    "preset": self.preset_name,
                    "total_nodes_estimated": self.total_calls
                    - 2,  # subtract strategy + synthesis
                },
                call_metrics={
                    "total_calls": self.total_calls,
                    "total_latency_ms": self.total_latency_ms,
                    "wall_time_ms": int((time.time() - start_time) * 1000),
                },
                mermaid_diagram="(single-tier mode — diagram available in track mode)",
            )

        self._log("\n" + "=" * 60)
        self._log(
            f"📊 COMPLETE | Calls: {result.call_metrics['total_calls']} | "
            f"Time: {result.call_metrics.get('wall_time_ms', 0)}ms"
        )
        self._log("=" * 60)

        return result

    async def _solve_with_tracks(self, query: str, context: str = "") -> AGoTResult:
        """Dispatch 4 track personas, each with internal AGoT, then converge."""
        self._log("🚀 Dispatching 4 track personas with AGoT sub-graphs...\n")

        start_time = time.time()
        track_names = ["A_DOMAIN", "B_ADVERSARIAL", "C_CROSS_DOMAIN", "D_ZERO_POINT"]
        track_results: dict[str, str] = {}

        # Run all 4 tracks concurrently, each with AGoT internally
        semaphore = asyncio.Semaphore(4)

        async def run_track(track_name: str):
            async with semaphore:
                self._log(f"  🔹 Track {track_name} starting AGoT sub-graph...")
                # Create a sub-controller for this track (reduced depth)
                sub_ctrl = AGoTController(
                    model=self.model_name,
                    preset="full",  # Each track uses full AGoT internally
                    verbose=False,
                )
                sub_ctrl.max_depth = max(0, self.max_depth - 1)

                # Prepend persona context
                persona_ctx = TRACK_PERSONAS.get(track_name, "")
                track_query = (
                    f"[PERSONA: {persona_ctx}]\n\n"
                    f"Analyze from this perspective:\n{query}"
                )

                result = await sub_ctrl._solve_recursive(
                    track_query, depth=0, parent_context=context
                )

                self.total_calls += sub_ctrl.total_calls
                self.total_latency_ms += sub_ctrl.total_latency_ms

                self._log(
                    f"  ✅ Track {track_name}: "
                    f"{sub_ctrl.total_calls} calls, "
                    f"{sub_ctrl.total_latency_ms}ms"
                )
                return track_name, result

        track_tasks = [run_track(tn) for tn in track_names]
        results = await asyncio.gather(*track_tasks)
        track_results = dict(results)

        # Measure inter-track agreement
        agreement = await self._measure_agreement(track_results)
        self._log(f"\n📊 Inter-track agreement: {agreement:.2f}")

        # Synthesize across tracks
        self._log("🔗 Cross-track synthesis...")
        track_synthesis_input = "\n\n".join(
            f"## {name} OUTPUT:\n{content[:2000]}"
            for name, content in track_results.items()
        )

        synthesis_prompt = (
            f"You are the SYNTHESIS ENGINE. Integrate insights from 4 "
            f"parallel reasoning tracks into a unified analysis.\n\n"
            f"ORIGINAL QUERY: {query}\n\n"
            f"TRACK OUTPUTS:\n{track_synthesis_input}\n\n"
            f"Instructions:\n"
            f"1. Identify convergence points\n"
            f"2. Resolve conflicts (Track B risks get priority)\n"
            f"3. Incorporate cross-domain insights\n"
            f"4. Produce final recommendation with confidence (1-10)\n"
        )
        synthesis = await self._llm_call(synthesis_prompt)

        # Adaptive convergence gate
        convergence_history = []
        threshold = self._adaptive_threshold(agreement)
        self._log(f"🛡️ Convergence gate (threshold: {threshold})...")

        gate_result = await self._convergence_gate(synthesis, agreement)
        convergence_history.append(gate_result)

        if not gate_result.get("passed", True):
            self._log(
                f"  ↩️ Gate failed ({gate_result.get('total_score', 0)}/{threshold}), iterating..."
            )
            # One refinement pass
            feedback = gate_result.get("critique", "Needs improvement")
            refined_prompt = (
                f"Refine this synthesis based on feedback:\n\n"
                f"FEEDBACK: {feedback}\n"
                f"SUGGESTIONS: {gate_result.get('suggestions', [])}\n\n"
                f"ORIGINAL SYNTHESIS:\n{synthesis[:3000]}\n\n"
                f"Provide improved synthesis:"
            )
            synthesis = await self._llm_call(refined_prompt)
            gate_result_2 = await self._convergence_gate(synthesis, agreement)
            convergence_history.append(gate_result_2)

        wall_time = int((time.time() - start_time) * 1000)

        return AGoTResult(
            synthesis=synthesis,
            graph_metadata={
                "preset": self.preset_name,
                "tracks_used": track_names,
                "inter_track_agreement": agreement,
                "convergence_threshold": threshold,
            },
            call_metrics={
                "total_calls": self.total_calls,
                "total_latency_ms": self.total_latency_ms,
                "wall_time_ms": wall_time,
            },
            mermaid_diagram=self._build_track_mermaid(track_results),
            convergence_history=convergence_history,
        )

    async def _measure_agreement(self, track_results: dict[str, str]) -> float:
        """Measure semantic agreement between track outputs (0-1)."""
        prompt = (
            "Rate the overall agreement between these 4 analyses on a scale of 0.0 to 1.0.\n"
            "0.0 = complete disagreement, 1.0 = complete agreement.\n\n"
            + "\n".join(f"Track {k}: {v[:500]}" for k, v in track_results.items())
            + "\n\nOutput ONLY a number between 0.0 and 1.0:"
        )
        response = await self._llm_call(prompt, temperature=0.3, max_tokens=64)
        try:
            match = re.search(r"(\d+\.?\d*)", response)
            return min(1.0, max(0.0, float(match.group(1)))) if match else 0.5
        except (ValueError, AttributeError):
            return 0.5

    def _adaptive_threshold(self, agreement: float) -> int:
        """Compute convergence threshold based on inter-track agreement."""
        if agreement > 0.8:
            return 70
        elif agreement > 0.5:
            return 85
        else:
            return 90

    async def _convergence_gate(self, synthesis: str, agreement: float) -> dict:
        """Run adversarial convergence gate with adaptive threshold."""
        threshold = self._adaptive_threshold(agreement)

        if agreement > 0.8:
            level = "HIGH"
        elif agreement > 0.5:
            level = "PARTIAL"
        else:
            level = "LOW"

        prompt = CONVERGENCE_GATE_PROMPT.format(
            synthesis=synthesis[:4000], agreement_level=level
        )
        response = await self._llm_call(prompt, temperature=0.3, max_tokens=1024)
        parsed = self._parse_json(response)

        score = parsed.get("total_score", 85)
        parsed["passed"] = score >= threshold
        parsed["threshold_used"] = threshold

        self._log(
            f"  📊 Gate score: {score}/{threshold} "
            f"{'✅ PASSED' if parsed['passed'] else '❌ NEEDS ITERATION'}"
        )
        return parsed

    def _build_track_mermaid(self, track_results: dict[str, str]) -> str:
        """Build Mermaid visualization for track-based reasoning."""
        lines = [
            "graph TD",
            '    Q["🎯 Query"] --> TA["Track A: Domain"]',
            '    Q --> TB["Track B: Adversarial"]',
            '    Q --> TC["Track C: Cross-Domain"]',
            '    Q --> TD["Track D: Zero-Point"]',
            '    TA --> S["🔗 Synthesis"]',
            "    TB --> S",
            "    TC --> S",
            "    TD --> S",
            '    S --> G{"🛡️ Convergence Gate"}',
            '    G -->|Pass| O["✅ Output"]',
            "    G -->|Fail| S",
        ]
        return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# CLI Interface
# ─────────────────────────────────────────────────────────────────────────────


async def main():
    parser = argparse.ArgumentParser(
        description="AGoT Orchestrator v5.0 — Adaptive Graph of Thoughts"
    )
    parser.add_argument("query", help="The query to analyze")
    parser.add_argument(
        "--mode",
        default="full",
        choices=["lite", "full", "tracks"],
        help="Reasoning mode: lite (Λ 21-40), full (Λ 41-60), tracks (Λ > 60)",
    )
    parser.add_argument("--context", default="", help="Additional context (inline)")
    parser.add_argument(
        "--context-file", default="", help="Path to file containing additional context"
    )
    parser.add_argument(
        "--output", default="", help="Path to save final output (creates parent dirs)"
    )
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Model to use")
    parser.add_argument("--quiet", action="store_true", help="Suppress verbose output")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    # Load context from file
    context = args.context
    if args.context_file:
        ctx_path = Path(args.context_file)
        if ctx_path.exists():
            context = ctx_path.read_text(encoding="utf-8")
            if not args.quiet:
                print(f"📄 Loaded context from {ctx_path} ({len(context)} chars)")

    controller = AGoTController(
        model=args.model, preset=args.mode, verbose=not args.quiet
    )

    result = await controller.solve(args.query, context)

    # Build output payload
    output_payload = {
        "query": args.query,
        "mode": args.mode,
        "synthesis": result.synthesis,
        "graph_metadata": result.graph_metadata,
        "call_metrics": result.call_metrics,
        "convergence_history": result.convergence_history,
        "mermaid_diagram": result.mermaid_diagram,
        "timestamp": datetime.now().isoformat(),
        "model": args.model,
    }

    # Save to file
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if args.json or args.output.endswith(".json"):
            output_path.write_text(
                json.dumps(output_payload, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        else:
            md_content = f"""# AGoT v5.0 Output

**Query**: {args.query}
**Mode**: {args.mode}
**Timestamp**: {output_payload["timestamp"]}
**Model**: {args.model}
**Total LLM Calls**: {result.call_metrics["total_calls"]}
**Wall Time**: {result.call_metrics.get("wall_time_ms", 0)}ms

---

{result.synthesis}

---

## Graph Metadata
```json
{json.dumps(result.graph_metadata, indent=2)}
```

## Mermaid Diagram
```mermaid
{result.mermaid_diagram}
```
"""
            output_path.write_text(md_content, encoding="utf-8")

        if not args.quiet:
            print(f"\n💾 Output saved to: {output_path}")

    # Print to stdout
    if args.json:
        print(json.dumps(output_payload, indent=2, ensure_ascii=False))
    else:
        print("\n" + "=" * 60)
        print("📋 FINAL SYNTHESIS")
        print("=" * 60)
        print(result.synthesis)
        print("\n" + "-" * 60)
        print(
            f"Mode: {args.mode} | Calls: {result.call_metrics['total_calls']} | "
            f"Time: {result.call_metrics.get('wall_time_ms', 0)}ms"
        )


if __name__ == "__main__":
    asyncio.run(main())
