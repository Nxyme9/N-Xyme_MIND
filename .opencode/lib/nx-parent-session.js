// NX-PARENT-SESSION v2.0 — Thin wrapper over session-registry.js
// Phase 1B of OMO Dispatch Integration
// All parent-child-agent tracking delegated to session-registry (single source of truth).
// Keeps only sessionToolsMap which is unique to this module.
//
// Used by: nx-background-manager.js, nx-dispatch-tools.js

import { registry } from "./session-registry.js"

// ─── STATE (only what registry doesn't track) ──────────────────────────
const sessionToolsMap = new Map()   // sessionID → tools record

// ─── PARENT-CHILD REGISTRATION (delegated to registry) ─────────────────
/**
 * Links a child session to its parent.
 * Delegates to session-registry's register() for parent-child tracking.
 */
export function registerChild(parentID, childID) {
  if (!parentID || !childID) return
  // ParentID is tracked on the child's record in registry
  registry.register(childID, { parentID })
}

/**
 * Gets all child sessions for a parent.
 * Delegates to session-registry.
 */
export function getChildren(parentID) {
  return registry.getChildren(parentID)
}

/**
 * Gets the parent session ID for a child.
 * Delegates to session-registry.
 */
export function getParent(childID) {
  return registry.getParent(childID)
}

/**
 * Traces ancestry to find the root session.
 * Delegates to session-registry.
 */
export function getRootSession(childID) {
  const result = registry.resolveRootAgent(childID)
  return result?.rootSessionID || childID
}

/**
 * Gets the full ancestry chain: [root, ..., parent, child]
 * Uses registry's parent lookups to build the chain.
 */
export function getAncestryChain(childID) {
  const chain = []
  let current = childID
  const visited = new Set()

  while (current && !visited.has(current)) {
    visited.add(current)
    chain.unshift(current)
    current = registry.getParent(current)
  }

  return chain
}

// ─── SESSION AGENT TRACKING (delegated to registry) ────────────────────
/**
 * Sets the agent name for a session.
 * Delegates to session-registry's register().
 */
export function setSessionAgent(sessionID, agentName) {
  if (!sessionID || !agentName) return
  registry.register(sessionID, { agent: agentName })
}

/**
 * Gets the agent name for a session.
 * Delegates to session-registry's lookup().
 */
export function getSessionAgent(sessionID) {
  return registry.lookup(sessionID)
}

// ─── SESSION TOOLS TRACKING (UNIQUE — not in registry) ─────────────────
/**
 * Sets the tool restrictions for a session.
 */
export function setSessionTools(sessionID, tools) {
  if (!sessionID || !tools) return
  sessionToolsMap.set(sessionID, tools)
}

/**
 * Gets the tool restrictions for a session.
 */
export function getSessionTools(sessionID) {
  return sessionToolsMap.get(sessionID) || null
}

// ─── HOOK HANDLER (delegated to registry) ──────────────────────────────
/**
 * Call this from session.created hook to auto-track sessions.
 * Delegates to session-registry's handleSessionCreated().
 */
export function handleSessionCreated(input) {
  registry.handleSessionCreated(input)
}

// ─── CLEANUP (delegated to registry + local tools cleanup) ─────────────
/**
 * Removes a session from all tracking maps.
 */
export function removeSession(sessionID) {
  registry.remove(sessionID)
  sessionToolsMap.delete(sessionID)
}

// ─── EXPORTS FOR DEBUGGING ────────────────────────────────────────────
export function getDebugInfo() {
  const regInfo = registry.getDebugInfo()
  return {
    ...regInfo,
    trackedTools: sessionToolsMap.size,
  }
}
