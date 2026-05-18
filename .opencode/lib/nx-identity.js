// NX-IDENTITY v1.1 — Parent agent resolution, session ancestry, agent name normalization
// Phase 1A of OMO Dispatch Integration
// Uses shared session-registry module for cross-plugin identity propagation
//
// Used by: nx-parent-session.js, nx-background-manager.js, nx-dispatch-tools.js

import { readFileSync, existsSync } from "fs"

import { registry } from "./session-registry.js"

import { ROOT, join } from "./shared-config.js"
const CONFIG_PATH = join(ROOT, "opencode.json")

// ─── STATE (local cache for backward compat) ──────────────────────────
const sessionDirectoryMap = new Map()  // sessionID → directory

// ─── AGENT REGISTRY ───────────────────────────────────────────────────
let _agentNames = null  // Cached list of registered agent names

function getAgentNames() {
  if (_agentNames) return _agentNames
  try {
    const cfg = JSON.parse(readFileSync(CONFIG_PATH, "utf8"))
    _agentNames = Object.keys(cfg.agent || {})
    return _agentNames
  } catch {
    return []
  }
}

// ─── PARENT IDENTITY RESOLUTION ───────────────────────────────────────
/**
 * Resolves the parent agent identity from tool context.
 * Priority: explicit agent → session registry → fallback
 */
export function resolveParentIdentity(toolContext) {
  const ctx = toolContext || {}

  // Priority 1: Explicit agent from tool context (OMO's primary path)
  if (ctx.agent && ctx.agent !== "default" && ctx.agent !== "undefined") {
    return {
      agent: ctx.agent,
      sessionID: ctx.sessionID || "",
      directory: ctx.directory || ROOT,
    }
  }

  // Priority 2: Shared session registry (populated by all plugins)
  if (ctx.sessionID) {
    const registeredAgent = registry.lookup(ctx.sessionID)
    if (registeredAgent) {
      return {
        agent: registeredAgent,
        sessionID: ctx.sessionID,
        directory: sessionDirectoryMap.get(ctx.sessionID) || ctx.directory || ROOT,
      }
    }
  }

  // Priority 3: Fallback to directory
  return {
    agent: "unknown",
    sessionID: ctx.sessionID || "",
    directory: ctx.directory || ROOT,
  }
}

// ─── AGENT NAME NORMALIZATION ─────────────────────────────────────────
/**
 * Case-insensitive agent name matching against registered agents.
 * Returns the exact registered name or null if not found.
 * Pure delegation to shared registry — single source of truth.
 * LOCAL FALLBACK REMOVED: registry.normalizeAgentName covers all cases.
 */
export function normalizeAgentName(input) {
  if (!input) return null
  return registry.normalizeAgentName(input)
}

// ─── SESSION DIRECTORY RESOLUTION ─────────────────────────────────────
/**
 * Gets the working directory for a session.
 * Falls back to ROOT if not tracked.
 */
export function resolveSessionDirectory(sessionID) {
  return sessionDirectoryMap.get(sessionID) || ROOT
}

// ─── ANCESTRY CHAIN ───────────────────────────────────────────────────
/**
 * Traces the parent-child chain from a session to root.
 * Returns [root, ..., parent, child] or [] if not found.
 * Uses shared registry's parent-child tracking.
 */
export function getAncestorChain(childID) {
  const chain = []
  let current = childID
  const visited = new Set()

  while (current && !visited.has(current)) {
    visited.add(current)
    chain.unshift(current)
    const parent = registry.getParent(current)
    if (!parent) break
    current = parent
  }

  return chain.length > 1 ? chain : []
}

// ─── DEPTH CALCULATION ────────────────────────────────────────────────
/**
 * Calculates how deep a session is in the parent-child tree.
 * Root session = depth 0.
 */
export function getSessionDepth(sessionID) {
  const chain = getAncestorChain(sessionID)
  return Math.max(0, chain.length - 1)
}

// ─── HOOK HANDLER ─────────────────────────────────────────────────────
/**
 * Call this from session.created hook to populate maps.
 * Delegates agent registration to the shared session registry.
 */
export function handleSessionCreated(input) {
  const sid = input?.sessionID || input?.id || ""
  if (!sid) return

  // Delegate agent registration to the shared session registry
  // (it handles title-based extraction, parent tracking, persistence)
  registry.handleSessionCreated(input)

  // Track directory locally (registry doesn't need this)
  const directory = input?.session?.directory || input?.directory || ROOT
  if (directory) {
    sessionDirectoryMap.set(sid, directory)
  }
}

// ─── EXPORTS FOR DEBUGGING ────────────────────────────────────────────
export function getDebugInfo() {
  const regInfo = registry.getDebugInfo()
  return {
    ...regInfo,
    directoryCount: sessionDirectoryMap.size,
    registeredAgents: getAgentNames(),
  }
}
