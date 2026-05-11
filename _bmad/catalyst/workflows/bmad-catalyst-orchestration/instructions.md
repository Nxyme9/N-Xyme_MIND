# Catalyst Orchestration Workflow Router

<workflow>

<critical>This router determines user state and delegates to workflow-specific sub-agents</critical>

<step n="1" goal="Detect user state and classify as FLOW, FRICTION, or ADAPT">
<action>Read fully and follow: ./steps/step-01-state-detection.md</action>
<action>Extract detected state and store as {{user_state}}</action>
</step>

<step n="2" goal="Select BMAD workflow based on user intent">
<action>Read fully and follow: ./steps/step-02-workflow-selection.md</action>
<action>Extract selected workflow and store as {{selected_workflow}}</action>
<action>Extract trigger phrases and store as {{trigger_phrases}}</action>
</step>

<step n="3" goal="Execute fractal delegation with depth tracking">
<action>Read fully and follow: ./steps/step-03-fractal-delegation.md</action>
<action>Track delegation depth and agent spawning</action>
<action>Store delegation results as {{delegation_results}}</action>
</step>

<step n="4" goal="Run quality gates on all outputs">
<action>Read fully and follow: ./steps/step-04-quality-gates.md</action>
<action>Collect quality metrics and store as {{quality_metrics}}</action>
</step>

<step n="5" goal="Generate benchmark report">
<action>Read fully and follow: ./steps/step-05-benchmark-report.md</action>
<action>Compile performance metrics and delegate results</action>
<action>Present final report to user</action>
</step>

</workflow>