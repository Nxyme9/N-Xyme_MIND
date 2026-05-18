// TOOL-TELEMETRY v1.0 — Track every tool call: success, failure, duration, agent, tool
// JSONL-backed with in-memory aggregation. No external deps.
// Auto-prunes records older than 7 days on init.

import { readFileSync, writeFileSync, appendFileSync, existsSync, mkdirSync, statSync } from "fs"
import { join, dirname } from "path"

const ROOT = "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND"
const TELEMETRY_DIR = join(ROOT, "data/telemetry")
const TELEMETRY_FILE = join(TELEMETRY_DIR, "tool-calls.jsonl")
const LOG_FILE = join(TELEMETRY_DIR, "telemetry.log")

function ensureDir() { try { mkdirSync(TELEMETRY_DIR, { recursive: true }) } catch {} }
function log(msg) { try { appendFileSync(LOG_FILE, `[${new Date().toISOString()}] ${msg}\n`) } catch {} }

// In-memory aggregation: agent → { tool → { ok, fail, total, last_ts } }
const _stats = new Map()
// Active calls: key → { agent, tool, ts } for duration tracking
const _active = new Map()

function _makeKey(agent, tool, unique) {
  return unique ? `${agent}::${tool}::${unique}` : `${agent}::${tool}`
}

function _aggregate(agent, tool, success, durationMs) {
  const key = _makeKey(agent, tool)
  if (!_stats.has(agent)) _stats.set(agent, new Map())
  const agentStats = _stats.get(agent)
  if (!agentStats.has(tool)) agentStats.set(tool, { ok: 0, fail: 0, total: 0, totalDuration: 0, lastTs: 0 })
  const stat = agentStats.get(tool)
  if (success) stat.ok++
  else stat.fail++
  stat.total++
  stat.totalDuration += durationMs
  stat.lastTs = Date.now()
}

export function recordStart(agent, tool, callId) {
  const key = _makeKey(agent, callId || tool, !!callId)
  _active.set(key, { agent, tool, ts: Date.now() })
}

export function recordEnd(agent, tool, callId, success, errorMsg) {
  const key = _makeKey(agent, callId || tool, !!callId)
  const start = _active.get(key)
  const duration = start ? Date.now() - start.ts : 0
  _active.delete(key)

  _aggregate(agent, tool, success, duration)

  ensureDir()
  try {
    appendFileSync(TELEMETRY_FILE, JSON.stringify({
      ts: Date.now(),
      agent, tool,
      success,
      durationMs: duration,
      error: errorMsg || null,
      session: globalThis.__telemetrySessionID || ""
    }) + "\n")
  } catch (e) { log(`write error: ${e.message}`) }

  // Auto-flush stats every 100th record
  const totalLines = existsSync(TELEMETRY_FILE)
    ? readFileSync(TELEMETRY_FILE, "utf8").trim().split("\n").filter(Boolean).length
    : 0
  if (totalLines % 100 === 0) log(`STATS: ${JSON.stringify(getSummary())}`)
}

export function getSummary() {
  const summary = { agents: {}, totals: { ok: 0, fail: 0, total: 0 } }
  for (const [agent, tools] of _stats) {
    summary.agents[agent] = {}
    for (const [tool, stat] of tools) {
      summary.agents[agent][tool] = { ...stat }
      summary.totals.ok += stat.ok
      summary.totals.fail += stat.fail
      summary.totals.total += stat.total
    }
  }
  return summary
}

export function getAgentStats(agent) {
  const tools = _stats.get(agent)
  if (!tools) return { total: 0, ok: 0, fail: 0, rate: 0, tools: [] }
  const entries = []
  let total = 0, ok = 0, fail = 0
  for (const [tool, stat] of tools) {
    entries.push({ tool, ...stat })
    total += stat.total
    ok += stat.ok
    fail += stat.fail
  }
  return { total, ok, fail, rate: total > 0 ? Math.round((ok / total) * 100) : 0, tools: entries }
}

export function getRecent(count = 50) {
  if (!existsSync(TELEMETRY_FILE)) return []
  try {
    const lines = readFileSync(TELEMETRY_FILE, "utf8").trim().split("\n").filter(Boolean)
    return lines.slice(-count).map(l => JSON.parse(l)).reverse()
  } catch { return [] }
}

export function getFailureRate(agent, minutes = 60) {
  const cutoff = Date.now() - minutes * 60 * 1000
  if (!existsSync(TELEMETRY_FILE)) return { rate: 0, total: 0, failed: 0 }
  try {
    const lines = readFileSync(TELEMETRY_FILE, "utf8").trim().split("\n").filter(Boolean)
    let total = 0, failed = 0
    for (const line of lines) {
      try {
        const r = JSON.parse(line)
        if (r.agent === agent && r.ts > cutoff) {
          total++
          if (!r.success) failed++
        }
      } catch {}
    }
    return { rate: total > 0 ? Math.round((failed / total) * 100) : 0, total, failed }
  } catch { return { rate: 0, total: 0, failed: 0 } }
}

// Prune records older than 7 days on load
ensureDir()
if (existsSync(TELEMETRY_FILE)) {
  try {
    const cutoff = Date.now() - 7 * 24 * 60 * 60 * 1000
    const lines = readFileSync(TELEMETRY_FILE, "utf8").trim().split("\n").filter(Boolean)
    const pruned = lines.filter(l => { try { return JSON.parse(l).ts > cutoff } catch { return false } })
    if (pruned.length < lines.length) {
      writeFileSync(TELEMETRY_FILE, pruned.join("\n") + (pruned.length ? "\n" : ""))
      log(`Pruned ${lines.length - pruned.length} old records`)
    }
  } catch {}
}

export const telemetry = {
  recordStart, recordEnd,
  getSummary, getAgentStats, getRecent, getFailureRate,
  _stats, _active,
}
export default telemetry
