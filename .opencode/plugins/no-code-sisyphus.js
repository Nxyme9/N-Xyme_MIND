// Tool guard — enforces per-agent tool scoping from agents/<name>/tools.json
// AND enforces opencode.json permission field at the plugin level.
// AND audits all tool calls for delete-bypass patterns.
// No hardcoded agent names. Reads config files every call.

import { readFileSync, writeFileSync, existsSync, appendFileSync, mkdirSync, readdirSync, statSync } from "fs"
import { dirname } from "path"

// Shared session registry for cross-plugin identity propagation
import { registry } from "../lib/session-registry.js"
import { telemetry } from "../lib/tool-telemetry.js"

// Project root — single source of truth for portability
import { ROOT as PROJECT_ROOT, join } from "../lib/shared-config.js"
const CONFIG_PATH = `${PROJECT_ROOT}/opencode.json`
const AGENTS_DIR = `${PROJECT_ROOT}/agents`
const AUDIT_DIR = `${PROJECT_ROOT}/data/audit`
const AUDIT_LOG = `${AUDIT_DIR}/calls.jsonl`
const ALERTS_LOG = `${AUDIT_DIR}/alerts.jsonl`
const NOTIFY_LOG = `${PROJECT_ROOT}/data/notifications/queue.jsonl`
const ACTIVE_AGENT_FILE = `${PROJECT_ROOT}/data/active-agent.json`

// Cross-call state: track reads per agent+file for read-then-write detection
const recentReads = new Map()  // key: "agent::filepath" → timestamp
// Session to agent mapping: maps subagent session_id to agent name
const sessionAgentMap = new Map()

try { mkdirSync(AUDIT_DIR, { recursive: true }) } catch {}

function auditLog(entry) {
  try { appendFileSync(AUDIT_LOG, JSON.stringify(entry) + "\n") } catch {}
}

function alertLog(alert) {
  try { appendFileSync(ALERTS_LOG, JSON.stringify({ ts: Date.now(), ...alert }) + "\n") } catch {}
}

function resolveAgentName(inputAgent, inputArgs, hookInput) {
  // Priority 1: _agent injected into args by nx-plugin
  if (inputArgs?._agent && inputArgs._agent !== "default" && inputArgs._agent !== "undefined") return inputArgs._agent

  // Priority 2: explicit agent from tool call context
  if (inputAgent && inputAgent !== "default" && inputAgent !== "undefined") return inputAgent

  // Priority 3: shared session registry (populated by ralph-autoloop tools + session.created hook)
  try {
    const sessionID = hookInput?.sessionID || inputArgs?.session_id || inputArgs?.sessionId || ""
    if (sessionID) {
      const registered = registry.lookup(sessionID)
      if (registered) return registered
    }
    if (sessionID) {
      const rootInfo = registry.resolveRootAgent(sessionID)
      if (rootInfo?.agent) return rootInfo.agent
    }
  } catch {}
  return ""
}

function loadTools(agent) {
  if (!agent) return null

  // Use registry to normalize agent name first (single source of truth)
  const normalized = registry.normalizeAgentName(agent)
  if (!normalized) return null

  // Derive directory from canonical agent name:
  // "Atlas - Plan Executor" → first word "Atlas" → "agents/atlas/tools/tools.json"
  // "Hephaestus - Builder" → "agents/hephaestus/tools/tools.json"
  const dirName = normalized.split(/[\s\-]+/)[0].toLowerCase()
  const path = `${AGENTS_DIR}/${dirName}/tools/tools.json`
  if (existsSync(path)) {
    return JSON.parse(readFileSync(path, "utf8"))
  }

  // Fallback: scan all agent directories for a matching name
  try {
    const agentDirs = readdirSync(AGENTS_DIR)
    for (const dir of agentDirs) {
      const p = `${AGENTS_DIR}/${dir}/tools/tools.json`
      if (!existsSync(p)) continue
      if (normalized.toLowerCase().includes(dir) || dir.includes(normalized.toLowerCase())) {
        return JSON.parse(readFileSync(p, "utf8"))
      }
    }
  } catch {}

  return null
}

// ─── CACHED loadConfig — avoids re-reading opencode.json on every tool call ──
let _configCache = null
let _configMtime = 0

function loadConfig() {
  try {
    if (!existsSync(CONFIG_PATH)) return null
    const stat = statSync(CONFIG_PATH)
    // Invalidate if file has been modified since last read
    if (_configCache && stat.mtimeMs === _configMtime) return _configCache
    _configCache = JSON.parse(readFileSync(CONFIG_PATH, "utf8"))
    _configMtime = stat.mtimeMs
    return _configCache
  } catch {
    return null
  }
}

function resolvePermission(agentName, toolName, config) {
  if (!config) return "allow"
  const perm = config.permission
  if (!perm) return "allow"
  if (typeof perm === "string") return perm
  if (agentName) {
    const agentDef = config.agent?.[agentName]
    if (agentDef?.permission) {
      const agentPerm = agentDef.permission
      if (typeof agentPerm === "string") return agentPerm
      if (agentPerm[toolName] !== undefined) return agentPerm[toolName]
    }
  }
  if (perm[toolName] !== undefined) return perm[toolName]
  return "allow"
}

// ─── ARGS SANITIZER — prevent credential leakage in audit logs ─────────
const SENSITIVE_KEYS = /^(api_key|apiKey|token|password|secret|credential|authorization|auth|private_key|passphrase)$/i
const SENSITIVE_PATTERNS = /(key|token|secret|password|credential|auth)/i

function sanitizeArgs(args) {
  if (!args || typeof args !== "object") return args
  const sanitized = {}
  for (const [key, value] of Object.entries(args)) {
    if (SENSITIVE_KEYS.test(key)) {
      sanitized[key] = "***REDACTED***"
    } else if (typeof value === "string" && value.length > 100 && SENSITIVE_PATTERNS.test(key)) {
      sanitized[key] = value.slice(0, 50) + "... [truncated]"
    } else {
      sanitized[key] = value
    }
  }
  return sanitized
}

function extractFilePath(args) {
  return args?.filePath || args?.path || args?.file_path || ""
}

function isDeleteBypass(tool, args, agentName) {
  const filePath = extractFilePath(args)

  // Pattern 1: edit with empty content = file wipe
  if (tool === "edit") {
    const newContent = args?.newString || ""
    const oldContent = args?.oldString || ""
    if (newContent === "" && oldContent.length > 10) {
      return { severity: "high", reason: `edit replaces ${oldContent.length} chars with empty string — potential wipe` }
    }
  }

  // Pattern 2: write with empty/single-byte content to existing-looking path
  if (tool === "write") {
    const content = args?.content || ""
    if (content.length <= 1 && filePath.match(/\.(js|py|rs|ts|json|md|go|rb|java)$/)) {
      return { severity: "high", reason: `write with ${content.length} chars to ${filePath} — potential overwrite` }
    }
  }

  // Pattern 3: batch_write with path list suggesting mass wipe
  if (tool === "batch_write") {
    const files = args?.files || []
    if (files.length >= 5) {
      return { severity: "medium", reason: `batch_write with ${files.length} files in one call` }
    }
  }

  return null
}

function detectSweepPattern(agentName, tool, args) {
  const filePath = extractFilePath(args)
  if (!filePath) return null

  const dir = dirname(filePath)
  if (dir === ".") return null

  // Check if this agent has been writing/editing to the same directory repeatedly
  const recentOps = []
  // We track per-directory operation counts in the audit log (checked post-hoc)
  // For real-time, we use a simplified heuristic
  const opsInDir = agentOps.get(agentName)?.[dir] || 0
  if (opsInDir >= 3) {
    return { severity: "medium", reason: `${opsInDir + 1} operations in ${dir} — possible sweep` }
  }

  return null
}

// Per-agent per-directory operation counter (for sweep detection)
const agentOps = new Map()

function trackAgentOp(agentName, dir) {
  if (!agentName) return
  if (!agentOps.has(agentName)) agentOps.set(agentName, {})
  const ops = agentOps.get(agentName)
  ops[dir] = (ops[dir] || 0) + 1
}

function checkReadBeforeWrite(agentName, tool, args) {
  const filePath = extractFilePath(args)
  if (!filePath || !agentName) return null

  const key = `${agentName}::${filePath}`

  if (tool === "read" || tool === "glob" || tool === "grep") {
    // Track reads for write-detection later
    recentReads.set(key, Date.now())
    return null
  }

  if ((tool === "write" || tool === "edit") && recentReads.has(key)) {
    const readTime = recentReads.get(key)
    const elapsed = Date.now() - readTime
    if (elapsed < 30000) {  // Within 30 seconds
      return { severity: "low", reason: `read then ${tool} ${filePath} within ${elapsed}ms` }
    }
  }

  return null
}


let _client = null

function storeActiveAgent(agentName, sessionId) {
  try {
    writeFileSync(ACTIVE_AGENT_FILE, JSON.stringify({ agent: agentName, session: sessionId || "", updated: Date.now() }))
  } catch {}
}

function notifyBlocked(agentName, tool, reason) {
  if (!_client) return
  const body = `❌ ${agentName || "default"} blocked: ${tool} (${reason})`
  try {
    _client.tui.showToast({ body: { title: "Blocked", message: body, variant: "error", duration: 4000 } })
  } catch {
    try { appendFileSync(NOTIFY_LOG, JSON.stringify({ ts: Date.now(), title: "Blocked", message: body, variant: "error" }) + "\n") } catch {}
  }
}

export const NoCodeSisyphusPlugin = async ({ project, client, $, directory, worktree }) => {
  _client = client
  return {
    "tool.execute.before": async (input, output) => {
      try {
        const args = input.args || {}
        const tool = input.tool || ""
        const agentName = resolveAgentName(input.agent || "", args, input)

        // Telemetry: track start
        telemetry.recordStart(agentName, tool, input?.sessionID)

        // ENFORCEMENT LAYER 1: opencode.json permission field
        const config = loadConfig()
        if (config) {
          const verdict = resolvePermission(agentName, tool, config)
          if (verdict === "deny") {
            auditLog({ ts: Date.now(), agent: agentName, tool, args: sanitizeArgs(args), verdict: "denied", reason: "permission_config" })
            notifyBlocked(agentName, tool, "permission denied in opencode.json")
            throw new Error(
              `❌ DENIED: "${tool}" not allowed for agent "${agentName || "default"}".\n` +
              `Root permission blocks this tool.`
            )
          }
        }

        // ENFORCEMENT LAYER 2: tools.json allowed/blocked/scoped (write/edit only)
        const writeTools = ["write", "edit", "apply_patch"]
        if (!writeTools.includes(tool)) return

        const toolsCfg = loadTools(input.agent || "")
        if (!toolsCfg) return

        if (toolsCfg.blocked?.includes(tool)) {
          auditLog({ ts: Date.now(), agent: agentName, tool, args: sanitizeArgs(args), verdict: "blocked", reason: "tools_blocked" })
          notifyBlocked(agentName, tool, "tool is in blocked list")
          throw new Error(
            `❌ BLOCKED: "${tool}" not allowed for this agent.\n` +
            `Allowed: ${toolsCfg.allowed.join(", ")}`
          )
        }

        if (toolsCfg.allowed && !toolsCfg.allowed.includes(tool)) {
          auditLog({ ts: Date.now(), agent: agentName, tool, args: sanitizeArgs(args), verdict: "blocked", reason: "tools_not_allowed" })
          notifyBlocked(agentName, tool, "not in allowed list")
          throw new Error(
            `❌ BLOCKED: "${tool}" not in agent's allowed tools.\n` +
            `Allowed: ${toolsCfg.allowed.join(", ")}`
          )
        }

        if (toolsCfg.scoped?.[tool]) {
          const filePath = (args?.filePath || args?.path || "").toLowerCase()
          const extensions = toolsCfg.scoped[tool]
          if (!extensions.some(ext => filePath.endsWith(ext))) {
            auditLog({ ts: Date.now(), agent: agentName, tool, args: sanitizeArgs(args), verdict: "scoped", reason: "extension_mismatch" })
            notifyBlocked(agentName, tool, `scope: only ${extensions.join(", ")} allowed`)
            throw new Error(
              `❌ SCOPED: "${tool}" only allowed for: ${extensions.join(", ")}`
            )
          }
        }

      } catch (e) {
        if (e.message.includes("DENIED") || e.message.includes("BLOCKED") || e.message.includes("SCOPED")) throw e
        auditLog({ ts: Date.now(), agent: agentName, tool, args: sanitizeArgs(args), verdict: "blocked", reason: "guard_error" })
        notifyBlocked(agentName, tool, "guard error — cannot verify permissions")
        throw new Error(`❌ BLOCKED: Tool guard error — cannot verify permissions for "${tool}": ${e.message}`)
      }
    },

    "tool.execute.after": async (input, output) => {
      try {
        const args = input.args || {}
        // RAW log of what agent identity opencode passes (updated to include registry lookup result)
        try {
          const regAgent = registry.lookup(input?.sessionID || "")
          appendFileSync("/tmp/agent_raw.jsonl", JSON.stringify({
            ts: Date.now(), rawAgent: input.agent, tool: input.tool,
            has_agent: !!input.agent, args_agent: args?._agent,
            registry_lookup: regAgent || "(none)",
            sid: input?.sessionID || args?.session_id || "",
            has_output: !!output, result_type: typeof output?.task_id
          }) + "\n")
        } catch {}
        const agentName = resolveAgentName(input.agent || "", args, input)
        const tool = input.tool || ""

        // Telemetry: track result — detect success/failure from output
        const isError = output?.isError || output?.error || (typeof output === "object" && output !== null && "error" in output)
        telemetry.recordEnd(agentName, tool, input?.sessionID, !isError, isError ? (output?.error || output?.message || "") : "")

        const filePath = extractFilePath(args)
        const dir = filePath ? dirname(filePath) : ""

        // Log every call (args sanitized to prevent credential leakage)
        auditLog({
          ts: Date.now(),
          agent: agentName,
          tool,
          args: sanitizeArgs({ filePath, ...args }),
          result: output?.content?.length || "no_output"
        })

        // Pattern 1: Delete bypass detection (edit→empty, write→tiny)
        const bypass = isDeleteBypass(tool, args, agentName)
        if (bypass) {
          alertLog({ agent: agentName, tool, args, ...bypass })
        }

        // Pattern 2: Read-then-write detection
        const readWrite = checkReadBeforeWrite(agentName, tool, args)
        if (readWrite) {
          alertLog({ agent: agentName, tool, args, ...readWrite })
        }

        // Pattern 3: Sweep detection (many ops in same dir)
        if (dir) {
          trackAgentOp(agentName, dir)
          const sweep = detectSweepPattern(agentName, tool, args)
          if (sweep) {
            alertLog({ agent: agentName, tool, args, ...sweep })
          }
        }

      } catch (e) {
        // Audit failures must never crash the tool call
      }
    }
  }
}
