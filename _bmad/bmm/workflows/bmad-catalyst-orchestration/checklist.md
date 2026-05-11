# Catalyst Orchestration Workflow - Validation Checklist

## Step 1: State Detection

- [ ] User input analyzed for state indicators
- [ ] State classified as FLOW, FRICTION, or ADAPT
- [ ] Context factors extracted from activeContext.md
- [ ] Session history checked for recent operations
- [ ] Mixed state (if applicable) identified
- [ ] State classification presented to user for confirmation
- [ ] Classification stored as {{user_state}}

## Step 2: Workflow Selection

- [ ] User request parsed for trigger keywords
- [ ] Matched to appropriate BMAD workflow
- [ ] Workflow existence validated in _bmad/bmm/workflows/
- [ ] SKILL.md read from selected workflow
- [ ] Trigger phrases extracted
- [ ] Workflow parameters prepared

## Step 3: Fractal Delegation

- [ ] Task complexity assessed (L1-L5)
- [ ] Max delegation depth determined
- [ ] Task decomposed into independent work units
- [ ] Dependencies identified between units
- [ ] Independent units grouped for parallel execution
- [ ] Agents spawned with depth tracking
- [ ] Delegation tree maintained
- [ ] Agent lifecycle managed (completion, timeout, failure)
- [ ] Depth counter maintained throughout workflow
- [ ] Delegation decisions logged

## Step 4: Quality Gates

- [ ] Output files identified for validation
- [ ] Gate 1 (Type Check) executed - 0 errors
- [ ] Gate 2 (Lint) executed - 0 errors
- [ ] Gate 3 (Format) executed - no changes needed
- [ ] Gate 4 (Tests) executed - all pass
- [ ] Gate 5 (Secrets Scan) executed - no secrets
- [ ] Gate 6 (Placeholders) executed - no TODOs
- [ ] Gate 7 (Agent Call) validated - spec followed
- [ ] Gate 8 (Security Paths) validated - secure
- [ ] Failures handled appropriately
- [ ] Quality metrics aggregated

## Step 5: Benchmark Report

- [ ] Delegation metrics compiled
- [ ] Quality metrics compiled
- [ ] Performance metrics compiled
- [ ] Report generated in markdown format
- [ ] Report saved to .sisyphus/benchmark-reports/
- [ ] Report presented to user

---

## Definition of Done

The workflow is complete when:

### Required Criteria (ALL must pass)

1. **State Detection Complete**
   - User state classified and confirmed
   - {{user_state}} stored

2. **Workflow Selection Complete**
   - BMAD workflow selected and validated
   - {{selected_workflow}} stored

3. **Fractal Delegation Complete**
   - All sub-agents spawned and completed
   - Delegation tree tracked
   - {{delegation_results}} stored

4. **Quality Gates Passed**
   - All 8 gates executed
   - Gates passed: 6+ (75%+)
   - {{quality_metrics}} stored

5. **Benchmark Report Generated**
   - Report saved to disk
   - Report presented to user
   - {{benchmark_report}} stored

### Quality Thresholds

- **Minimum Quality Score:** 75%
- **Maximum Failed Gates:** 2
- **Required Gates:** Type Check, Lint, Secrets Scan

### Post-Completion

- [ ] User has reviewed benchmark report
- [ ] Any quality failures acknowledged by user
- [ ] Recommendations noted for future runs
- [ ] Delegation log updated in .sisyphus/
- [ ] Session state updated with workflow results

---

## Issues Found

### Critical Issues (must fix before completion)

-

### Minor Issues (can be addressed later)

-

### Missing Information (to note for user)

-

---

## Metrics Summary

| Metric | Target | Actual |
|--------|--------|--------|
| Quality Score | 75%+ | |
| Gates Passed | 6+/8 | |
| Agents Spawned | Task-dependent | |
| Max Depth | L1-L2: 1, L3: 2, L4: 3, L5: 4 | |
| Workflow Duration | < 5 minutes | |
| User State Detection | 100% accuracy | |

---

## Completion Criteria

All items in the following sections must be checked:

- ✓ Step 1: State Detection
- ✓ Step 2: Workflow Selection
- ✓ Step 3: Fractal Delegation
- ✓ Step 4: Quality Gates
- ✓ Step 5: Benchmark Report
- ✓ Quality Thresholds Met
- ✓ Post-Completion Actions

The workflow is complete when:

1. All 5 steps executed successfully
2. Quality threshold met (75%+ gates passed)
3. Benchmark report generated and presented
4. User acknowledges completion
5. Delegation log updated