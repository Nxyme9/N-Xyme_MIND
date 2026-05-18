// NX-PLUGIN v2.2 — _agent INJECTION + BMAD skills + ML context
// Hooks: session.created, tool.execute.before/after, experimental.session.compacting
// Auto-injects _agent + queries ML for task-relevant context + suggests BMAD skills

import { readFileSync, writeFileSync, appendFileSync, existsSync, mkdirSync } from "fs"
import { dirname } from "path"

// Shared session registry for cross-plugin identity propagation
import { registry } from "../lib/session-registry.js"

// Project root — single source of truth for portability
import { ROOT, join } from "../lib/shared-config.js"
const LOG = join(ROOT, "data/sessions/nx-plugin.log")

// BMAD keyword → skill mapping (mirrors bmad-mcp/server.py KEYWORD_MAP)
const BMAD_KEYWORDS = {
  "brainstorm": "skill(\"bmad-brainstorming\") — idea generation",
  "plan": "skill(\"bmad-create-architecture\") — architecture decisions",
  "build": "skill(\"bmad-dev-story\") — structured execution",
  "review": "skill(\"bmad-code-review\") — quality review",
  "research": "skill(\"bmad-domain-research\") — domain research",
  "technical": "skill(\"bmad-technical-research\") — technical research",
  "market": "skill(\"bmad-market-research\") — market research",
  "memory": "skill(\"bmad-memory-consolidate\") — save session to memory",
  "recall": "skill(\"bmad-memory-recall\") — recall from memory",
  "retro": "skill(\"bmad-retrospective\") — post-epic review",
  "sprint-plan": "skill(\"bmad-sprint-planning\") — sprint planning",
  "sprint-status": "skill(\"bmad-sprint-status\") — sprint status check",
  "architecture": "skill(\"bmad-create-architecture\") — solution design",
  "ux": "skill(\"bmad-create-ux-design\") — UX specifications",
  "prd": "skill(\"bmad-edit-prd\") — edit product requirements",
  "validate": "skill(\"bmad-validate-prd\") — validate PRD",
  "qa": "skill(\"bmad-qa-generate-e2e-tests\") — generate tests",
  "orchestrate": "skill(\"nx-sisyphus-orchestrate\") — orchestrate agents",
  "hotload": "skill(\"nx-hephaestus-hotload\") — hot-load code",
  "party": "skill(\"bmad-party-mode\") — multi-agent discussion",
  "opgrade": "skill(\"nx-total-opgrade\") — full system upgrade",
  "shard": "skill(\"bmad-shard-doc\") — split documents",
  "distill": "skill(\"bmad-distillator\") — compress documents",
}

// Module-level init wrapped — never throw at module scope
;(() => { try { mkdirSync(dirname(LOG), { recursive: true }) } catch {} })()

function log(msg) {
  try { appendFileSync(LOG, `[${new Date().toISOString()}] ${msg}\n`) } catch {}
}

function getAgent(input) {
  // Priority 1: Explicit agent from input (rare — OpenCode doesn't set it)
  const explicit = input?.agent
  if (explicit && explicit !== "default" && explicit !== "undefined") return explicit

  // Priority 2: Shared session registry (populated by ralph-autoloop + session.created hook)
  const sessionID = input?.sessionID || ""
  if (sessionID) {
    const registered = registry.lookup(sessionID)
    if (registered) return registered
  }

  // Priority 3: Extract from session title if available in input
  const title = input?.session?.title || input?.title || ""
  if (title) {
    const extracted = registry.extractAgentFromTitle(title)
    if (extracted) return registry.normalizeAgentName(extracted) || extracted
  }

  return ""
}

export const NxPlugin = async ({ project, client, $, directory, worktree }) => {
  try {
    log("initialized")
  } catch (e) {
    log(`init error: ${e.message}`)
  }

  return {
    "session.created": async (input) => {
      try {
        const sid = input?.id || input?.sessionID || ""

        // Register in shared session registry (extracts agent from title)
        registry.handleSessionCreated(input)

        const agent = getAgent(input)
        if (sid && agent) log(`session.created: ${sid.slice(0,12)} → ${agent}`)

        // Periodic persist (every 10 sessions)
        try {
          const count = registry.getDebugInfo().totalSessions
          if (count > 0 && count % 10 === 0) registry.persist()
        } catch {}

        // ML Context Injection — query local ML for task-relevant context
        // Runs automatically on every session start, no skill loading needed
        const msg = input?.messages?.[0]?.content || ""

        // Dictation catch-up: inject messages queued while I was away
        try {
          const queuePath = "/tmp/dictation-queue.jsonl"
          const seenPath = "/tmp/dictation-seen.json"
          let seen = {}
          try { seen = JSON.parse(readFileSync(seenPath, "utf8")) } catch {}
          const unseen = []
          if (existsSync(queuePath)) {
            const lines = readFileSync(queuePath, "utf8").trim().split("\n").filter(Boolean)
            for (const line of lines) {
              try {
                const d = JSON.parse(line)
                if (d?.text && !seen[d.ts] && Date.now() - d.ts < 3600000) {
                  const sanitized = String(d.text).slice(0, 2000)
                  if (!/^(ignore all|disregard|system prompt|you are now)/i.test(sanitized)) {
                    unseen.push({ ...d, text: sanitized })
                  }
                  seen[d.ts] = true
                }
              } catch {}
            }
            if (unseen.length > 0) {
              const inject = unseen.map(d => `🎤 dictation: "${d.text}" → ${d.routed} @ ${d.confidence}`).join("\n")
              if (input?.messages?.[0]?.content) {
                input.messages[0].content = inject + "\n---\n" + input.messages[0].content
              }
              writeFileSync(seenPath, JSON.stringify(seen))
            }
          }
        } catch {}
        // AUTO-CONTEXT INJECTION: Match user message against holographic memory
        // and inject relevant context into first message (if within token budget)
        if (msg && msg.length > 20) {
          try {
            // Agent-specific context budgets (from nx_agents.json model assignments)
            const AGENT_BUDGETS = {
              "Catalyst": 1048576, "Hephaestus - Builder": 1048576,
              "Atlas - Plan Executor": 1048576, "Hermes - Memory & Personal": 1048576,
              "Mnemosyne - Debugger": 1048576, "Agent Builder": 1048576,
              "Prometheus - Planner": 1048576, "Librarian - Research": 1048576,
              "Momus - Critic": 1048576, "Oracle - Architecture": 1048576,
              "Cortex - Memory & Knowledge": 1048576, "Mr. White - Chemistry": 1048576,
              "Master Debugger": 1048576, "Red Team": 1048576,
              "System Architect": 1048576, "Explore - Search": 204800,
              "Metis - Consultant": 204800, "Sisyphus Junior - Code Writer": 204800,
              "Jarvis - Personal Assistant": 204800, "Kairos - Personal Therapist": 204800,
              "Phi-4 Reasoner": 262144, "Scalpel - Code Dissector": 1048576,
              "Vision Analyst": 1048576,
            }
            const agentName = getAgent(input) || "default"
            const contextBudget = AGENT_BUDGETS[agentName] || 1048576
            const maxInjectTokens = Math.floor(contextBudget * 0.15)
            const approxTokens = (s) => Math.ceil(String(s).length / 4)

            // Quick check: if message alone is already too large, skip injection
            const msgTokens = approxTokens(msg)
            if (msgTokens > maxInjectTokens * 0.5) {
              log(`CONTEXT SKIP: msg too large (${msgTokens} tok, budget ${maxInjectTokens})`)
            } else {
              // Extract meaningful keywords from message (words >3 chars, lowercase)
              const words = msg.toLowerCase().replace(/[^a-z0-9\s]/g, "").split(/\s+/).filter(w => w.length > 3)
              if (words.length > 0) {
                const holoPath = join(ROOT, "data/memory/holographic-memory.json")
                if (existsSync(holoPath)) {
                  const holo = JSON.parse(readFileSync(holoPath, "utf8"))
                  // Score each entry by keyword match count
                  const scored = []
                  for (const entry of holo) {
                    const content = (entry.content || "").toLowerCase()
                    const category = (entry.category || "").toLowerCase()
                    const combined = content + " " + category
                    let matchCount = 0
                    for (const word of words) {
                      if (combined.includes(word)) matchCount++
                    }
                    if (matchCount > 0) {
                      scored.push({
                        entry: entry,
                        score: matchCount / words.length,
                        matchCount
                      })
                    }
                  }
                  scored.sort((a, b) => b.score - a.score)
                  const topMatches = scored.slice(0, 3)
                  if (topMatches.length > 0) {
                    const contextLines = topMatches.map((m, i) => {
                      const e = m.entry
                      const content = String(e.content || "").slice(0, 500)
                      return `[${i+1}] (${e.category || "general"}) ${content}`
                    })
                    const contextStr = "## Relevant Context\n" + contextLines.join("\n\n")
                    const contextTokens = approxTokens(contextStr)
                    if (msgTokens + contextTokens <= maxInjectTokens) {
                      if (input?.messages?.[0]?.content) {
                        input.messages[0].content = contextStr + "\n\n---\n" + input.messages[0].content
                        log(`CONTEXT INJECT: ${topMatches.length} holographic entries for "${msg.slice(0,40)}..." (${contextTokens} tok)`)
                      }
                    } else {
                      log(`CONTEXT SKIP: context too large (${contextTokens} tok, budget ${maxInjectTokens})`)
                    }
                  } else {
                    log(`CONTEXT: no matches in ${holo.length} holographic entries for keywords: ${words.slice(0,5).join(", ")}`)
                  }
                }
              }
            }
          } catch (e2) {
            log(`ML context error: ${e2.message}`)
          }
        }
      } catch (e) {
        log(`session.created error: ${e.message}`)
      }
    },
    "tool.execute.before": async (input, output) => {
      try {
        const sid = input?.sessionID || ""
        const tool = input?.tool || ""
        const agent = getAgent(input)

        // Inject _agent into output.args so MCP servers can gate per-agent
        if (agent && output?.args && typeof output.args === "object") {
          if (!output.args._agent) {
            output.args._agent = agent
          }
        }

        if (tool === "task" && agent) {
          log(`before: tool=${tool} sid=${sid.slice(0,12)} agent=${agent}`)
        }
      } catch (e) {
        log(`before error: ${e.message}`)
      }
    },
    "tool.execute.after": async (input, output) => {
      try {
        const agent = getAgent(input)
        const result = typeof output === "string" ? output : JSON.stringify(output).slice(0, 200)
        appendFileSync("/tmp/nx-plugin-traffic.jsonl", JSON.stringify({
          ts: Date.now(),
          tool: input?.tool,
          agent,
          result_preview: result
        }) + "\n")

        // BMAD skill suggestion: check if tool output/args match a keyword
        const toolName = input?.tool || ""
        if (["read", "write", "edit", "bash", "task", "search_code"].includes(toolName)) {
          const text = result.toLowerCase()
          for (const [keyword, suggestion] of Object.entries(BMAD_KEYWORDS)) {
            if (text.includes(keyword)) {
              log(`BMAD suggestion for ${agent}: ${keyword} → ${suggestion}`)
              break
            }
          }
        }
      } catch {}
    },
    "experimental.session.compacting": async (input, output) => {
      try {
        const root = readFileSync(join(ROOT, "ROOT.md"), "utf-8")
        output.context.push(`\n## NX-PLUGIN PERSISTENT CONTEXT\n${root.slice(0, 2000)}`)
        log("compacting: context injected")
      } catch (e) {
        log(`compacting error: ${e.message}`)
      }
    },
  }
}
