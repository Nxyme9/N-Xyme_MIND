// Auto-generated from opencode.json — do not edit manually
// Source: NAP protocol agent definitions v3.0

const AGENTS = {
  "Agent Builder": {
    description: "Designs and creates other agents from task descriptions. Uses templates for structure, meta-prompting for content.",
    mode: "subagent",
    model: "opencode/deepseek-v4-flash-free",
  },
  "Atlas - Plan Executor": {
    description: "Plan executor — takes plans, tracks execution, reports progress. Alternative orchestrator for execution-heavy sessions.",
    mode: "subagent",
    model: "opencode/deepseek-v4-flash-free",
  },
  "Cortex - Memory & Knowledge": {
    description: "Memory, data, embeddings, knowledge graph, context offloading, session consolidation.",
    mode: "subagent",
    model: "opencode/deepseek-v4-flash-free",
  },
  "Explore - Search": {
    description: "Codebase search agent. Finds patterns, files, implementations via grep and search tools.",
    mode: "subagent",
    model: "opencode/minimax-m2.5-free",
  },
  "Hephaestus - Builder": {
    description: "Parallel hot-loaded implementation worker. Uses Structured CoT for reliable code generation.",
    mode: "primary",
    model: "opencode/deepseek-v4-flash-free",
  },
  "Jarvis - Personal Assistant": {
    description: "Dedicated persistent personal assistant — dictation always routes here. Voice→text→action pipeline.",
    mode: "all",
    model: "opencode/minimax-m2.5-free",
  },
  "Kairos - Personal Therapist": {
    description: "Personal therapist — ADHD, CBT, executive function, RSD-safe communication, trauma-informed care.",
    mode: "subagent",
    model: "opencode/minimax-m2.5-free",
  },
  "Librarian - Research": {
    description: "External research specialist. Searches docs, OSS code, web for best practices and examples.",
    mode: "subagent",
    model: "opencode/deepseek-v4-flash-free",
  },
  "Metis - Consultant": {
    description: "Pre-planning consultant. Surfaces hidden assumptions and AI failure points.",
    mode: "subagent",
    model: "opencode/minimax-m2.5-free",
  },
  "Momus - Critic": {
    description: "Rigorous adversarial plan critic. Finds gaps and unstated assumptions.",
    mode: "subagent",
    model: "opencode/deepseek-v4-flash-free",
  },
  "Mr. White - Chemistry": {
    description: "Chemistry lab specialist. Procedures, safety, calculations, documentation.",
    mode: "subagent",
    model: "opencode/deepseek-v4-flash-free",
  },
  "Oracle - Architecture": {
    description: "High-IQ read-only architecture consultant. Deep analysis, never writes code.",
    mode: "subagent",
    model: "opencode/deepseek-v4-flash-free",
  },
  "Phi-4 Reasoner": {
    description: "Deep reasoning specialist. Multi-step logic, math, analysis.",
    mode: "subagent",
    model: "opencode/ring-2.6-1t-free",
  },
  "Prometheus - Planner": {
    description: "Strategic plan builder with dependency ordering and verification.",
    mode: "subagent",
    model: "opencode/deepseek-v4-flash-free",
  },
  "Scalpel - Code Dissector": {
    description: "Code dissector. Decompose, understand, extract, Frankenstein stitch, architect freely.",
    mode: "subagent",
    model: "opencode/qwen3.6-plus-free",
  },
  "Catalyst": {
    description: "Primary orchestrator — plans, delegates, coordinates. NEVER writes code.",
    mode: "primary",
    model: "opencode/deepseek-v4-flash-free",
  },
  "Sisyphus Junior - Code Writer": {
    description: "Fast code writer for simple changes, docs, and config edits.",
    mode: "subagent",
    model: "opencode/minimax-m2.5-free",
  },
  "System Architect": {
    description: "Full system awareness — reads live source files, understands architecture, detects changes automatically.",
    mode: "all",
    model: "opencode/deepseek-v4-flash-free",
  },
  "Vision Analyst": {
    description: "Visual and media analysis specialist. Images, screenshots, diagrams.",
    mode: "subagent",
    model: "opencode/qwen3.6-plus-free",
  },
};

module.exports = { AGENTS };
