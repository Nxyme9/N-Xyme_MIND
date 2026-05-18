// SESSION-REGISTRY v1.0 — Cross-plugin session→agent identity resolver
// Singleton module shared by all plugins via import.
//
// PROBLEM: OpenCode's `input.agent` is always empty in plugin hooks.
// This module solves it by:
//   1. Capturing sessionID→agentName at session creation time
//   2. Extracting agent from session titles ("[subagent] AgentName: ...")
//   3. Persisting to disk for durability across restarts
//   4. Traversing parent chains to resolve root agent for child sessions
//
// USAGE:
//   import { registry } from "../lib/session-registry.js"
//   registry.register(sessionID, { agent: "Hephaestus", ... })
//   const agent = registry.lookup(sessionID)          // "Hephaestus"
//   const root  = registry.resolveRootAgent(sessionID) // root session's agent

import { readFileSync, writeFileSync, existsSync, mkdirSync, appendFileSync } from "fs"
import { dirname } from "path"

// Project root — single source of truth for portability
import { ROOT, join } from "./shared-config.js"

// ─── PERSISTENT STORAGE ────────────────────────────────────────────────
const REGISTRY_DIR = join(ROOT, "data/identity")
const REGISTRY_FILE = join(REGISTRY_DIR, "session-registry.json")
const LOG_FILE = join(ROOT, "data/sessions/registry.log")

// ─── IN-MEMORY STATE ───────────────────────────────────────────────────
// Map<sessionID, { agent: string, title: string, parentID: string, created: string }>
const _sessions = new Map()

// Map<parentID, Set<childID>> — reverse index for parent chain traversal
const _children = new Map()

// ─── LOGGING ───────────────────────────────────────────────────────────
function log(msg) {
  try { appendFileSync(LOG_FILE, `[${new Date().toISOString()}] ${msg}\n`) } catch {}
}

// ─── TITLE-BASED AGENT EXTRACTION ──────────────────────────────────────
/**
 * Extracts agent name from session title format used by ralph-autoloop:
 *   "[subagent] Hephaestus - Builder: implement story X"
 *   "[sync] Hephaestus - Builder: implement story X"
 *   "[subagent] Catalyst: research topic"
 *
 * Also matches bare agent names at start of title.
 *
 * Returns extracted agent name or null.
 */
export function extractAgentFromTitle(title) {
  if (!title || typeof title !== "string") return null

  // Pattern 1: [subagent] AgentName: ... or [sync] AgentName: ...
  const taggedMatch = title.match(/^\[(?:subagent|sync)\]\s*([^:]+?)\s*:\s*/)
  if (taggedMatch) {
    const agent = taggedMatch[1].trim()
    if (agent && agent.length > 0 && agent.length < 100) return agent
  }

  // Pattern 2: AgentName: task description (no prefix)
  const directMatch = title.match(/^([A-Za-z][A-Za-z\s\-]+?)\s*:\s*/)
  if (directMatch) {
    const agent = directMatch[1].trim()
    if (agent && agent.length > 0 && agent.length < 80) return agent
  }

  return null
}

// ─── AGENT NAME NORMALIZATION ──────────────────────────────────────────
/**
 * Try to normalize a raw agent name against the registered agent list
 * from opencode.json config.
 */
let _agentNames = null

function getRegisteredAgentNames() {
  if (_agentNames) return _agentNames
  try {
    const configPath = join(ROOT, "opencode.json")
    if (existsSync(configPath)) {
      const cfg = JSON.parse(readFileSync(configPath, "utf8"))
      _agentNames = Object.keys(cfg.agent || {})
      return _agentNames
    }
  } catch {}
  return []
}

/**
 * Normalize: partial case-insensitive match against registered agents.
 * "hephaestus" → "Hephaestus - Builder"
 * "atlas" → "Atlas - Plan Executor"
 */
export function normalizeAgentName(input) {
  if (!input) return null
  const names = getRegisteredAgentNames()
  const lower = input.toLowerCase().trim()

  // Exact match
  if (names.includes(input.trim())) return input.trim()

  // Case-insensitive match
  for (const name of names) {
    if (name.toLowerCase() === lower) return name
  }

  // Partial match
  for (const name of names) {
    if (name.toLowerCase().includes(lower) || lower.includes(name.toLowerCase())) return name
  }

  return null // No match found — caller must handle
}

// ─── REGISTRY OPERATIONS ───────────────────────────────────────────────

/**
 * Register a session explicitly (from delegation tools that know the agent).
 * Called by ralph-autoloop.js after client.session.create().
 */
export function register(sessionID, { agent, title, parentID } = {}) {
  if (!sessionID) return

  // Normalize agent name for consistency across all registrations
  const normalizedAgent = agent ? (normalizeAgentName(agent) || agent) : null

  const record = {
    agent: normalizedAgent,
    title: title || "",
    parentID: parentID || "",
    created: new Date().toISOString(),
    source: agent ? "explicit" : "title",
  }

  _sessions.set(sessionID, record)

  // Track parent-child relationships
  if (parentID) {
    const children = _children.get(parentID) || new Set()
    children.add(sessionID)
    _children.set(parentID, children)
  }

  // Persist incrementally (append to log + periodic full flush)
  log(`REGISTER ${sessionID.slice(0, 12)} → agent="${agent || "(from title)"}" parent="${(parentID || "").slice(0, 12)}"`)

  return record
}

/**
 * Look up agent name for a session ID.
 * Returns agent name string or null if not found.
 * Chain: explicit registry → title extraction → parent chain → root
 */
export function lookup(sessionID) {
  if (!sessionID) return null

  // Phase 1: Direct lookup in registry
  const record = _sessions.get(sessionID)
  if (record?.agent) return record.agent

  // Phase 2: Try to extract from stored title
  if (record?.title) {
    const extracted = extractAgentFromTitle(record.title)
    if (extracted) {
      const normalized = normalizeAgentName(extracted)
      record.agent = normalized
      return normalized
    }

    // Phase 2b: Try matching entire title against registered agent names
    // e.g., "Sisyphus - Orchestrator" (the session title when agent is selected)
    const matched = matchTitleToAgent(record.title, getRegisteredAgentNames())
    if (matched) {
      record.agent = matched
      return matched
    }
  }

  // Phase 3: Walk parent chain
  if (record?.parentID) {
    return lookup(record.parentID)
  }

  return null
}

/**
 * Try to match a session title against known agent names.
 * Handles cases like title="Sisyphus - Orchestrator" matching agent "Sisyphus - Orchestrator".
 */
function matchTitleToAgent(title, agentNames) {
  if (!title || !agentNames || agentNames.length === 0) return null

  const titleLower = title.toLowerCase().trim()

  for (const name of agentNames) {
    // Exact case-insensitive match
    if (name.toLowerCase() === titleLower) return name
    // Title starts with agent name (e.g., "Sisyphus - Orchestrator: doing work")
    if (titleLower.startsWith(name.toLowerCase() + ":") || titleLower.startsWith(name.toLowerCase() + " ")) return name
    // Agent name includes the title (e.g., title="catalyst" matches "Catalyst - Orchestrator")
    if (name.toLowerCase().includes(titleLower)) return name
  }

  return null
}

/**
 * Resolve the root session's agent by traversing parent chain upward.
 * Returns { agent, rootSessionID, depth } or null.
 */
export function resolveRootAgent(sessionID) {
  if (!sessionID) return null

  const visited = new Set()
  let current = sessionID
  let depth = 0

  while (current && !visited.has(current)) {
    visited.add(current)
    const record = _sessions.get(current)

    // Check if this session has a known agent
    if (record?.agent) {
      return { agent: record.agent, rootSessionID: current, depth }
    }

    // Check title for extractable agent
    if (record?.title) {
      const extracted = extractAgentFromTitle(record.title)
      if (extracted) {
        const normalized = normalizeAgentName(extracted)
        record.agent = normalized
        return { agent: normalized, rootSessionID: current, depth }
      }

      // Try matching full title against registered agent names
      const matched = matchTitleToAgent(record.title, getRegisteredAgentNames())
      if (matched) {
        record.agent = matched
        return { agent: matched, rootSessionID: current, depth }
      }
    }

    // Walk up
    if (record?.parentID) {
      current = record.parentID
      depth++
    } else {
      break
    }
  }

  return null
}

/**
 * Get full record for a session.
 */
export function resolve(sessionID) {
  return _sessions.get(sessionID) || null
}

/**
 * Check if a session is registered.
 */
export function has(sessionID) {
  return _sessions.has(sessionID)
}

/**
 * Get all child session IDs for a parent.
 */
export function getChildren(parentID) {
  return _children.get(parentID) || new Set()
}

/**
 * Get parent session ID for a child.
 */
export function getParent(sessionID) {
  const record = _sessions.get(sessionID)
  return record?.parentID || null
}

// ─── HOOK HANDLER ──────────────────────────────────────────────────────
/**
 * Process session.created hook input.
 * Auto-registers sessions from the hook, extracting agent from title
 * when the agent field is empty (which is always the case).
 *
 * Call this from plugin session.created hooks.
 */
export function handleSessionCreated(input) {
  const sessionID = input?.sessionID || input?.id || ""
  if (!sessionID) return

  // Skip if already registered with explicit agent
  if (_sessions.has(sessionID) && _sessions.get(sessionID)?.agent) return

  const rawAgent = input?.session?.agent || input?.agent || ""
  const title = input?.session?.title || input?.title || ""
  const parentID = input?.session?.parentID || input?.parentID || ""

  // If agent is explicitly provided (rare), use it
  let agent = null
  let source = "none"

  if (rawAgent && rawAgent !== "default" && rawAgent !== "undefined") {
    agent = rawAgent
    source = "explicit"
  } else if (title) {
    // Extract agent from title format "[subagent] AgentName: ..."
    agent = extractAgentFromTitle(title)
    if (agent) {
      // Normalize: "hephaestus" → "Hephaestus - Builder"
      const normalized = normalizeAgentName(agent)
      if (normalized) agent = normalized
      source = "title"
    } else {
      // Fallback: match entire title against registered agent names
      // e.g., title="Catalyst" → agent="Catalyst"
      agent = matchTitleToAgent(title, getRegisteredAgentNames())
      if (agent) source = "title"
    }
  }

  register(sessionID, { agent, title, parentID })
}

// ─── PERSISTENCE ───────────────────────────────────────────────────────

function ensureDir() {
  try { mkdirSync(REGISTRY_DIR, { recursive: true }) } catch {}
}

/**
 * Persist the registry to disk as JSON.
 */
export function persist() {
  try {
    ensureDir()
    const data = {
      version: 1,
      updated: new Date().toISOString(),
      sessions: Object.fromEntries(
        Array.from(_sessions.entries()).map(([id, record]) => [id, record])
      ),
      parentChild: Object.fromEntries(
        Array.from(_children.entries()).map(([parent, children]) => [parent, Array.from(children)])
      ),
    }
    writeFileSync(REGISTRY_FILE, JSON.stringify(data, null, 2))
    log(`PERSIST: ${_sessions.size} sessions, ${_children.size} parents`)
  } catch (e) {
    log(`persist error: ${e.message}`)
  }
}

/**
 * Load the registry from disk.
 */
export function load() {
  try {
    if (!existsSync(REGISTRY_FILE)) {
      log("LOAD: no existing registry file")
      return
    }
    const data = JSON.parse(readFileSync(REGISTRY_FILE, "utf8"))
    if (data.sessions) {
      for (const [id, record] of Object.entries(data.sessions)) {
        _sessions.set(id, record)
      }
    }
    if (data.parentChild) {
      for (const [parent, children] of Object.entries(data.parentChild)) {
        _children.set(parent, new Set(children))
      }
    }
    log(`LOAD: ${_sessions.size} sessions, ${_children.size} parents restored`)
  } catch (e) {
    log(`load error: ${e.message}`)
  }
}

// ─── MAINTENANCE ───────────────────────────────────────────────────────

/**
 * Remove a session from the registry.
 */
export function remove(sessionID) {
  const record = _sessions.get(sessionID)
  if (record?.parentID) {
    const siblings = _children.get(record.parentID)
    if (siblings) {
      siblings.delete(sessionID)
      if (siblings.size === 0) _children.delete(record.parentID)
    }
  }
  _children.delete(sessionID)
  _sessions.delete(sessionID)
}

/**
 * Get debug/diagnostic information.
 */
export function getDebugInfo() {
  return {
    totalSessions: _sessions.size,
    totalParents: _children.size,
    withAgent: Array.from(_sessions.values()).filter(r => r.agent).length,
    withTitle: Array.from(_sessions.values()).filter(r => r.title).length,
    registeredAgents: getRegisteredAgentNames(),
    filePath: REGISTRY_FILE,
  }
}

/**
 * Get all session registrations (for debugging/logging).
 */
export function getAllSessions() {
  return Array.from(_sessions.entries())
}

// ─── LOAD STATUS — callers can detect failures ─────────────────────────
/**
 * Load status tracking so callers can detect if the registry failed to load.
 * `loadStatus` is set after auto-load attempt on import.
 */
export let loadStatus = { loaded: false, error: null, timestamp: null }

// ─── AUTO-LOAD ON IMPORT ───────────────────────────────────────────────
// Load persisted state immediately so it's available from plugin init onward.
try {
  load()
  loadStatus = { loaded: true, error: null, timestamp: new Date().toISOString() }
} catch (e) {
  loadStatus = { loaded: false, error: e.message, timestamp: new Date().toISOString() }
}

// ─── EXPORT SINGLETON (named + default) ───────────────────────────────
// Named export for destructured imports: import { registry } from "..."
// Default export for direct imports: import registry from "..."
export const registry = {
  register,
  lookup,
  resolve,
  resolveRootAgent,
  has,
  getChildren,
  getParent,
  handleSessionCreated,
  extractAgentFromTitle,
  normalizeAgentName,
  persist,
  load,
  remove,
  getDebugInfo,
  getAllSessions,
  get loadStatus() { return loadStatus },  // expose mutable load status
}

export default registry
