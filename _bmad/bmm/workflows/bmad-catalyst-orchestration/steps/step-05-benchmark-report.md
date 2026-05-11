# Step 5: Benchmark Report

**Goal:** Generate benchmark report with performance metrics and delegation results

---

## Benchmark Report Generation

Compile all metrics from previous steps into a comprehensive benchmark report.

### Metrics Captured

#### Delegation Metrics
- Total agents spawned
- Max depth reached
- Parallel vs sequential execution ratio
- Agent success rate
- Average latency per agent type

#### Quality Metrics
- Gates passed/failed
- Overall quality score
- Error types and counts
- Files validated

#### Performance Metrics
- Total workflow duration
- Time per step
- Token usage (if available)
- Memory usage (if available)

---

## Execution

<step n="5.1" goal="Compile delegation metrics">
<action>Aggregate delegation tree from Step 3</action>
<action>Calculate delegation statistics</action>
<action>Store as {{delegation_stats}}</action>
</step>

<step n="5.2" goal="Compile quality metrics">
<action>Aggregate quality gate results from Step 4</action>
<action>Calculate quality score</action>
<action>Store as {{quality_stats}}</action>
</step>

<step n="5.3" goal="Compile performance metrics">
<action>Calculate total workflow duration</action>
<action>Calculate time per step</action>
<action>Collect any available resource metrics</action>
<action>Store as {{performance_stats}}</action>
</step>

<step n="5.4" goal="Generate report">
<action>Format all metrics into benchmark report</action>
<action>Save report to .sisyphus/benchmark-reports/</action>
<action>Present report to user</action>
</step>

---

## Report Format

```markdown
# Catalyst Orchestration Benchmark Report
**Date:** {timestamp}
**User:** {user_name}
**Task:** {task_description}

## Summary
- **Status:** SUCCESS | PARTIAL | FAILED
- **Duration:** {total_ms}ms
- **Quality Score:** {score}%

## Delegation Metrics
- Agents Spawned: {count}
- Max Depth: {depth}
- Success Rate: {percentage}
- Parallel Execution: {ratio}

## Quality Gates
- Gates Passed: {count}
- Gates Failed: {count}
- Files Validated: {count}

## Step Breakdown
| Step | Duration | Status |
|------|-----------|--------|
| 1. State Detection | {ms}ms | PASS/FAIL |
| 2. Workflow Selection | {ms}ms | PASS/FAIL |
| 3. Fractal Delegation | {ms}ms | PASS/FAIL |
| 4. Quality Gates | {ms}ms | PASS/FAIL |
| 5. Benchmark Report | {ms}ms | PASS/FAIL |

## Recommendations
- [Suggestions for improvement]
```

---

## Output

- **benchmark_report:** Complete report in markdown
- **delegation_stats:** Aggregated delegation metrics
- **quality_stats:** Aggregated quality metrics
- **performance_stats:** Aggregated performance metrics
- **report_path:** Path where report was saved