# Phase 6: Prompt Evolution — Detailed Masterplan

> **Duration:** 3-4 days
> **Risk:** MEDIUM
> **Dependencies:** Phase 3 (Meta-Learning) complete
> **Oracle Review:** REQUIRED for Task 6.2

---

## Executive Summary

Phase 6 enables **automatic prompt improvement** based on delegation outcomes. Uses GEPA-inspired approach: instead of random trial-and-error (RL), we use LLM reflection to identify what to fix.

**Key Insight (GEPA - ICLR 2026 Oral):**
- 35x fewer rollouts than RL
- 90x cheaper than Claude Opus
- Uses LLM reflection instead of scalar rewards

**GO/NO-GO:** Only proceed after ≥100 delegation outcomes collected.

---

## Tasks Overview

| Task | Name | Effort | Risk | Dependencies |
|------|------|--------|------|--------------|
| 6.1 | Outcome-Linked Scoring | 0.5 day | LOW | Phase 4 (Multi-dim rewards) |
| 6.2 | LLM Refinement | 1.5 days | HIGH | 6.1 |
| 6.3 | A/B Testing | 1 day | MEDIUM | 6.1 + 6.2 |
| 6.4 | Prompt Registry | 0.5 day | LOW | 6.1 |

---

## Task 6.1: Outcome-Linked Scoring

### What It Does
Link each prompt version to actual delegation outcomes (success rate, latency, quality).

### Formula
```
score = 0.60 × success_rate 
      + 0.25 × latency_score 
      + 0.15 × token_efficiency

latency_score = 1.0 if latency < 5s else 0.5
token_efficiency = min(total_tokens / 50, 1.0)
```

### Implementation

```python
# packages/learning_engine/prompts/scorer.py

class PromptScorer:
    def __init__(self, db_path: str = ".sisyphus/routing.db"):
        self.db_path = db_path
    
    def score_prompt(self, prompt_name: str) -> dict:
        """Calculate score for a prompt version."""
        
        outcomes = self._get_outcomes(prompt_name)
        if not outcomes:
            return {"score": 0.0, "samples": 0}
        
        # Success rate
        success_rate = sum(1 for o in outcomes if o['success']) / len(outcomes)
        
        # Latency score
        latency_score = sum(
            1.0 if o['latency_ms'] < 5000 else 0.5 
            for o in outcomes
        ) / len(outcomes)
        
        # Token efficiency
        avg_tokens = sum(o.get('tokens', 0) for o in outcomes) / len(outcomes)
        token_efficiency = min(avg_tokens / 50, 1.0)
        
        # Composite
        score = (0.60 * success_rate + 
                 0.25 * latency_score + 
                 0.15 * token_efficiency)
        
        return {
            "score": score,
            "samples": len(outcomes),
            "success_rate": success_rate,
            "latency_score": latency_score,
            "token_efficiency": token_efficiency
        }
    
    def _get_outcomes(self, prompt_name: str) -> list:
        """Fetch outcomes for this prompt."""
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        rows = conn.execute("""
            SELECT success, latency_ms, tokens_used, prompt_version
            FROM outcomes 
            WHERE prompt_version = ?
            ORDER BY timestamp DESC
            LIMIT 100
        """, (prompt_name,)).fetchall()
        conn.close()
        
        return [
            {"success": r[0], "latency_ms": r[1], "tokens": r[2]}
            for r in rows
        ]
```

### Verification
```bash
.venv/bin/python3 -c "
from packages.learning_engine.prompts.scorer import PromptScorer
s = PromptScorer()
score = s.score_prompt('hephaestus-default')
print(f'Score: {score}')
"
```

### Success Criteria
- [ ] Score range 0.0-1.0
- [ ] Updates after each delegation
- [ ] Minimum 10 samples for reliable score

---

## Task 6.2: LLM Refinement

### What It Does
Use LLM to analyze failed prompts and suggest improvements. **Hybrid mode**: use LLM only when heuristic plateaus (saves 70% cost).

### Trigger Condition
```python
USE_LLM_REFINEMENT = (
    complexity_score > 0.7 or  # Task too complex for heuristic
    heuristic_plateau or        # No improvement in 10 attempts
    first_time_task             # Never seen this task type
)
```

### Implementation

```python
# packages/learning_engine/prompts/llm_refiner.py

class LLMRefiner:
    def __init__(self, model_endpoint: str = "http://localhost:8080"):
        self.endpoint = model_endpoint
    
    def refine(self, prompt: str, failed_outcomes: list) -> str:
        """Analyze failures and propose improved prompt."""
        
        # Build failure summary
        failure_summary = self._summarize_failures(failed_outcomes)
        
        # Get LLM suggestion
        suggestion = self._llm_reflect(prompt, failure_summary)
        
        return suggestion
    
    def _summarize_failures(self, outcomes: list) -> str:
        """Create failure summary for LLM."""
        if not outcomes:
            return "No failures recorded"
        
        types = {}
        for o in outcomes:
            if not o.get('success'):
                failure_type = o.get('failure_type', 'unknown')
                types[failure_type] = types.get(failure_type, 0) + 1
        
        return "; ".join(f"{k}: {v}x" for k, v in types.items())
    
    def _llm_reflect(self, prompt: str, failure_summary: str) -> str:
        """Use LLM to reflect on prompt improvements."""
        
        system_prompt = """You are a prompt engineering expert.
Given a prompt and failure summary, suggest a specific improvement.
Return ONLY the improved prompt, no explanation."""
        
        user_prompt = f"""Current prompt:
{prompt}

Failure summary:
{failure_summary}

Improve the prompt to address these failures:"""
        
        # Call local LLM
        response = requests.post(
            self.endpoint + "/v1/chat/completions",
            json={
                "model": "default",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.3
            }
        )
        
        return response.json()['choices'][0]['message']['content']
```

### Cost Optimization
- Heuristic first: ~$0 (rule-based)
- LLM fallback: ~$0.01 per call
- **Hybrid:** Only use LLM when heuristic fails 3+ times

### Success Criteria
- [ ] LLM triggers only when needed
- [ ] Refinements improve score by >10%
- [ ] Cost < 10% of pure LLM approach

---

## Task 6.3: A/B Testing

### What It Does
Statistically compare prompt versions to determine winner.

### Statistical Setup
- **Test:** Z-test for proportions
- **Minimum samples:** 100 per variant
- **Parameters:** α = 0.05, power = 0.80

### Implementation

```python
# packages/learning_engine/prompts/ab_test.py

class ABTestRunner:
    def __init__(self, scorer: PromptScorer):
        self.scorer = scorer
    
    def run_test(self, variant_a: str, variant_b: str) -> dict:
        """Run A/B test between two prompt versions."""
        
        outcomes_a = self._get_outcomes(variant_a)
        outcomes_b = self._get_outcomes(variant_b)
        
        # Check minimum samples
        if len(outcomes_a) < 100 or len(outcomes_b) < 100:
            return {"status": "insufficient_data", "a": len(outcomes_a), "b": len(outcomes_b)}
        
        # Calculate success rates
        rate_a = sum(1 for o in outcomes_a if o['success']) / len(outcomes_a)
        rate_b = sum(1 for o in outcomes_b if o['success']) / len(outcomes_b)
        
        # Z-test
        z_score = self._z_test(rate_a, rate_b, len(outcomes_a), len(outcomes_b))
        p_value = self._p_value(z_score)
        
        winner = variant_a if rate_a > rate_b else variant_b
        confident = p_value < 0.05
        
        return {
            "status": "complete",
            "variant_a": variant_a,
            "variant_b": variant_b,
            "rate_a": rate_a,
            "rate_b": rate_b,
            "z_score": z_score,
            "p_value": p_value,
            "winner": winner if confident else None,
            "confident": confident
        }
    
    def _z_test(self, r1, r2, n1, n2):
        """Calculate Z-score for two proportions."""
        import math
        pooled = (r1 * n1 + r2 * n2) / (n1 + n2)
        se = math.sqrt(pooled * (1 - pooled) * (1/n1 + 1/n2))
        return (r1 - r2) / se if se > 0 else 0
```

### Success Criteria
- [ ] Minimum 100 samples per variant
- [ ] Detects 5%+ difference with 80% power
- [ ] Auto-promotes winner

---

## Task 6.4: Prompt Registry

### What It Does
Version control for prompts: track versions, deprecate old ones, rollback capability.

### Schema

```sql
CREATE TABLE prompt_versions (
    id INTEGER PRIMARY KEY,
    prompt_name TEXT NOT NULL,
    version INTEGER NOT NULL,
    prompt_text TEXT NOT NULL,
    score REAL DEFAULT 0.0,
    outcome_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deprecated_at TIMESTAMP,
    UNIQUE(prompt_name, version)
);

CREATE TABLE prompt_relationships (
    parent_id INTEGER,
    child_id INTEGER,
    relationship TEXT,  -- 'refined_from', 'ab_test_of', 'rollout_of'
    FOREIGN KEY(parent_id) REFERENCES prompt_versions(id),
    FOREIGN KEY(child_id) REFERENCES prompt_versions(id)
);
```

### Operations

```python
# packages/learning_engine/prompts/registry.py

class PromptRegistry:
    def __init__(self, db_path: str = ".sisyphus/routing.db"):
        self.db_path = db_path
    
    def create_version(self, name: str, text: str) -> int:
        """Create new prompt version."""
        version = self._get_next_version(name)
        
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("""
            INSERT INTO prompt_versions (prompt_name, version, prompt_text)
            VALUES (?, ?, ?)
        """, (name, version, text))
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()
        return new_id
    
    def deprecate(self, name: str, version: int):
        """Mark version as deprecated."""
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            UPDATE prompt_versions 
            SET deprecated_at = datetime('now')
            WHERE prompt_name = ? AND version = ?
        """, (name, version))
        conn.commit()
        conn.close()
    
    def rollback(self, name: str, steps: int = 1) -> str:
        """Rollback N versions."""
        current = self.get_current(name)
        target_version = current['version'] - steps
        
        old = self.get_version(name, target_version)
        return old['prompt_text']
    
    def get_current(self, name: str) -> dict:
        """Get latest active version."""
        # Implementation
        pass
```

### Keep Last 3 Versions
- Automatic cleanup of versions > 3 back
- Archive instead of delete

### Success Criteria
- [ ] Version history tracked
- [ ] Rollback works
- [ ] Deprecation logged

---

## Go/No-Go Criteria

| Criterion | Threshold |
|-----------|-----------|
| Prompt scoring | Updates within 1 delegation |
| LLM refinement | Cost < 10% of pure LLM |
| A/B test detection | 5%+ difference at 80% power |
| Registry rollback | Works within 100ms |

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| LLM cost too high | MEDIUM | MEDIUM | Hybrid mode (heuristic first) |
| A/B inconclusive | MEDIUM | LOW | Increase samples, extend test |
| Version conflicts | LOW | MEDIUM | Registry with locking |

---

## Files Modified

| File | Action | Description |
|------|--------|-------------|
| `packages/learning_engine/prompts/scorer.py` | CREATE | Outcome-linked scoring |
| `packages/learning_engine/prompts/llm_refiner.py` | CREATE | LLM-based refinement |
| `packages/learning_engine/prompts/ab_test.py` | CREATE | A/B testing |
| `packages/learning_engine/prompts/registry.py` | CREATE | Version control |

---

## Rollback

```bash
# Disable prompt evolution
echo "PROMPT_EVOLUTION_ENABLED=false" >> .env

# Fall back to static prompts
# (use current version only, no evolution)
```

---

*Phase 6 complete. See Phase 7 for Bayesian confidence.*
