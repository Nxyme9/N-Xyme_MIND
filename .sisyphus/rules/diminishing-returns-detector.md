# Auto-Detect Diminishing Returns — Rule 11 (LLM-Powered)

## The Concept

Use a **lightweight local LLM** (Ollama) to analyze optimization cycles and auto-detect when it's "not worth it" to continue.

**Why LLM over formula?**
- Understands nuance and context
- Detects patterns humans miss
- Provides natural language explanations
- Adapts to different problem domains
- No cloud dependency (local Ollama)

## Implementation

```python
# diminishing_returns_detector.py
import requests

OLLAMA_URL = "http://localhost:11434"
MODEL = "qwen2.5-coder:7b"  # Fast, good reasoning, local

class DiminishingReturnsDetector:
    """Use local LLM to detect when optimization cycles stop being valuable."""

    def __init__(self, model: str = MODEL):
        self.model = model
        self.cycles = []

    def add_cycle(self, cycle_num: int, new_items: list[str], context: str = ""):
        """Record an optimization cycle."""
        self.cycles.append({
            "cycle": cycle_num,
            "new_items": new_items,
            "count": len(new_items),
            "context": context,
        })

    def should_continue(self) -> dict:
        """Ask the LLM if we should keep optimizing."""
        if len(self.cycles) < 3:
            return {"continue": True, "phase": "GREEN", "reason": "Too early to tell"}

        prompt = self._build_analysis_prompt()
        response = self._query_llm(prompt)
        return self._parse_response(response)

    def _build_analysis_prompt(self) -> str:
        """Build the analysis prompt from cycle history."""
        cycles_text = ""
        total_items = 0
        for c in self.cycles:
            total_items += c["count"]
            cycles_text += f"\nCycle {c['cycle']} ({c['context']}): {c['count']} new items\n"
            for item in c["new_items"][:5]:
                cycles_text += f"  - {item}\n"
            if c["count"] > 5:
                cycles_text += f"  ... and {c['count'] - 5} more\n"

        return f"""You are an optimization analyst. Analyze these optimization cycles and determine if diminishing returns have been hit.

CYCLES:
{cycles_text}

TOTAL: {total_items} items across {len(self.cycles)} cycles

ANALYZE:
1. Are recent cycles finding genuinely NEW patterns, or repeating variations?
2. Is IMPACT decreasing compared to earlier items?
3. Are we finding STRUCTURAL insights or SURFACE improvements?
4. Would continuing yield >5% improvement?

RESPOND EXACTLY:
PHASE: [GREEN/YELLOW/RED/NOISE]
CONTINUE: [YES/NO]
REASON: [1-2 sentences]
CONFIDENCE: [0-100%]

PHASES:
- GREEN: >10% impact, keep going
- YELLOW: 5-10%, one more then reassess
- RED: <5%, STOP and build
- NOISE: <2%, wasting time"""

    def _query_llm(self, prompt: str) -> str:
        """Query local Ollama LLM."""
        try:
            resp = requests.post(
                f"{OLLAMA_URL}/v1/chat/completions",
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                    "temperature": 0.1,  # Low temp = consistent
                },
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except:
            return self._fallback()

    def _parse_response(self, response: str) -> dict:
        """Parse LLM response into structured result."""
        result = {"continue": True, "phase": "GREEN", "reason": "", "confidence": 50}
        for line in response.strip().split("\n"):
            if line.startswith("PHASE:"):
                result["phase"] = line.split(":")[1].strip()
            elif line.startswith("CONTINUE:"):
                result["continue"] = "YES" in line.upper()
            elif line.startswith("REASON:"):
                result["reason"] = line.split(":")[1].strip()
            elif line.startswith("CONFIDENCE:"):
                try:
                    result["confidence"] = int(line.split(":")[1].strip().replace("%", ""))
                except:
                    pass
        return result

    def _fallback(self) -> str:
        """Formula fallback if LLM unavailable."""
        if len(self.cycles) < 3:
            return "PHASE: GREEN\nCONTINUE: YES\nREASON: Too early\nCONFIDENCE: 50%"
        recent = [c["count"] for c in self.cycles[-3:]]
        avg = sum(recent) / len(recent)
        if avg > 15: return f"PHASE: GREEN\nCONTINUE: YES\nREASON: Formula fallback, avg {avg:.0f}/cycle\nCONFIDENCE: 60%"
        elif avg > 8: return f"PHASE: YELLOW\nCONTINUE: YES\nREASON: Formula fallback, avg {avg:.0f}/cycle\nCONFIDENCE: 60%"
        elif avg > 3: return f"PHASE: RED\nCONTINUE: NO\nREASON: Formula fallback, avg {avg:.0f}/cycle\nCONFIDENCE: 60%"
        else: return f"PHASE: NOISE\nCONTINUE: NO\nREASON: Formula fallback, avg {avg:.0f}/cycle\nCONFIDENCE: 60%"
```

## Hybrid Approach (Best of Both)

```python
def should_continue(self) -> dict:
    """Hybrid: LLM + formula fallback."""
    if not self._ollama_available():
        return self._fallback()  # Formula backup
    try:
        return self._query_and_parse()
    except:
        return self._fallback()  # Formula backup on error
```

## LLM vs Formula

| Aspect | Formula | LLM |
|--------|---------|-----|
| Context awareness | ❌ | ✅ |
| Pattern recognition | ❌ Simple | ✅ Complex |
| Explanation | ❌ Numbers | ✅ Natural language |
| Adaptability | ❌ Fixed | ✅ Domain-aware |
| Speed | ✅ Instant | ⚠️ 5-10s |
| Reliability | ✅ Always | ⚠️ Needs Ollama |

**Recommendation**: Use LLM as primary, formula as fallback.

## Integration

1. After each cycle, `detector.add_cycle(num, items, context)`
2. Call `detector.should_continue()`
3. If RED/NOISE with >70% confidence → **STOP, start building**
4. If YELLOW → one more cycle, then reassess
5. If GREEN → keep optimizing

## The Rule

> **Auto-detect diminishing returns using a local LLM (Ollama). When the LLM says RED/NOISE with >70% confidence, STOP planning and START building. Falls back to formula if LLM unavailable.**
