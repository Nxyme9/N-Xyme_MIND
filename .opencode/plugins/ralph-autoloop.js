// RALPH AUTO-LOOP v2 — OMO Ralph Loop Port
// Hooks: session.created, message.updated, experimental.session.compacting
// Tools: call_omo_agent, delegate_task, tui_notify
//
// Frontmatter .md state survives restarts (data/ralph-state/active.md)
// Detects <promise>DONE</promise> / <promise>VERIFIED</promise> in model output
// Auto-injects continuation prompts on each iteration (rate-limited to 3s)
// Ultrawork mode: DONE → Oracle verification gate → VERIFIED required
// ULW aliases: ulw_start = ralph_start(ultrawork=true)

import { readFileSync, writeFileSync, existsSync, appendFileSync, mkdirSync, unlinkSync } from "fs"
import { execSync } from "child_process"
import { dirname } from "path"

// Shared session registry for cross-plugin identity propagation
import { registry } from "../lib/session-registry.js"

// Project root — single source of truth for portability
import { ROOT, join } from "../lib/shared-config.js"
const STATE_FILE = join(ROOT, "data/ralph-state/active.md")
const LOG = join(ROOT, "data/sessions/ralph-debug.log")
const NOTIFY_LOG = join(ROOT, "data/notifications/queue.jsonl")

const DEFAULT_MAX_ITERATIONS = 100
const DEFAULT_COMPLETION_PROMISE = "DONE"
const ULTRAWORK_VERIFICATION_PROMISE = "VERIFIED"
const MIN_INJECTION_INTERVAL = 3000

const lastInjectionTime = new Map()

// ─── LOGGING ───────────────────────────────────────────────────────────

function log(msg) {
  try { appendFileSync(LOG, `[${new Date().toISOString()}] ${msg}\n`) } catch {}
}

// ─── NOTIFICATION ──────────────────────────────────────────────────────

async function notify(client, { title, message, variant = "info", duration = 3000 }) {
  log(`NOTIFY [${variant}] ${title}: ${message}`)
  try {
    await client.tui.showToast({ body: { title, message, variant, duration } })
    return
  } catch {}
  try {
    appendFileSync(NOTIFY_LOG, JSON.stringify({ ts: Date.now(), title, message, variant, duration, fallback: "file" }) + "\n")
  } catch {}
}

// ─── FRONTMATTER PARSING (shared format with Python MCP tools) ─────────
// State file format:
//   ---
//   key: value
//   key: "string value"
//   active: true
//   iteration: 5
//   ---
//   <prompt body text>

function parseFrontmatter(content) {
  const match = content.match(/^---\n([\s\S]*?)\n---\n?([\s\S]*)$/)
  if (!match) return { data: {}, body: content.trim() }
  const data = {}
  for (const line of match[1].split('\n').filter(Boolean)) {
    const colon = line.indexOf(':')
    if (colon === -1) continue
    const key = line.slice(0, colon).trim()
    let val = line.slice(colon + 1).trim()
    if (val.startsWith('"') && val.endsWith('"')) val = val.slice(1, -1)
    else if (val.startsWith("'") && val.endsWith("'")) val = val.slice(1, -1)
    else if (val === 'true') val = true
    else if (val === 'false') val = false
    else if (val === 'undefined' || val === 'null') val = undefined
    else {
      const num = Number(val)
      if (!isNaN(num) && val !== '') val = num
    }
    data[key] = val
  }
  return { data, body: match[2].trim() }
}

function buildFrontmatter(state) {
  const data = { ...state }
  const prompt = data.prompt || ''
  delete data.prompt
  const lines = ['---']
  for (const [key, val] of Object.entries(data)) {
    if (val === undefined || val === null) continue
    if (typeof val === 'string') lines.push(`${key}: "${val.replace(/\\/g, '\\\\').replace(/"/g, '\\"')}"`)
    else if (typeof val === 'boolean') lines.push(`${key}: ${val}`)
    else lines.push(`${key}: ${val}`)
  }
  lines.push('---')
  if (prompt) lines.push(prompt)
  return lines.join('\n')
}

// ─── STATE HELPERS ─────────────────────────────────────────────────────

function ensureStateDir() {
  try { mkdirSync(dirname(STATE_FILE), { recursive: true }) } catch {}
}

function loadState() {
  try {
    if (!existsSync(STATE_FILE)) return null
    const content = readFileSync(STATE_FILE, 'utf-8')
    if (!content.trim()) return null
    const { data, body } = parseFrontmatter(content)
    if (data.active !== true) return null
    return { ...data, prompt: body }
  } catch (e) {
    log(`loadState error: ${e.message}`)
    return null
  }
}

function saveState(state) {
  try {
    ensureStateDir()
    writeFileSync(STATE_FILE, buildFrontmatter(state), 'utf-8')
    return true
  } catch (e) {
    log(`saveState error: ${e.message}`)
    return false
  }
}

function clearState() {
  try {
    if (existsSync(STATE_FILE)) unlinkSync(STATE_FILE)
    return true
  } catch (e) {
    log(`clearState error: ${e.message}`)
    return false
  }
}

// ─── PROMISE TAG DETECTION ─────────────────────────────────────────────

function escapeRegex(str) {
  return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

function buildPromisePattern(promise) {
  return new RegExp(`<promise>\\s*${escapeRegex(promise)}\\s*<\\/promise>`, 'is')
}

function detectPromiseInText(text, promise) {
  if (!text || !promise) return false
  const pattern = buildPromisePattern(promise)
  return pattern.test(text)
}

// ─── COMPILE FEEDBACK BRIDGE ───────────────────────────────────────────

function getCompilePatterns(task) {
  // Query pattern memory for similar compilations
  const script = join(ROOT, "scripts/compile-pattern-memory.py")
  if (!existsSync(script)) return ""
  try {
    const query = (task || "").slice(0, 200)
    const result = execSync(
      `python3 "${script}" format-prompt "${query.replace(/"/g, '\\"')}" --k 3 --max-chars 1500`,
      { timeout: 5000, encoding: "utf-8", stdio: ["pipe", "pipe", "ignore"] }
    ).toString().trim()
    return result ? "\n" + result : ""
  } catch (e) {
    log(`compile patterns error: ${e.message}`)
    return ""
  }
}

// ─── PROMPT BUILDERS (from OMO ralph-loop) ─────────────────────────────

function buildContinuationPrompt(state) {
  const maxLabel = typeof state.max_iterations === 'number' ? state.max_iterations : 'unbounded'
  const prefix = state.ultrawork ? 'ultrawork ' : ''

  // Inject compile patterns from memory to guide the next iteration
  const compilePatterns = getCompilePatterns(state.prompt)

  return `${prefix}─── RALPH LOOP [${state.iteration}/${maxLabel}]

Your previous attempt did not output the completion promise. Continue working on the task.

IMPORTANT:
- Review your progress so far
- Continue from where you left off
- When FULLY complete, output: <promise>${state.completion_promise}</promise>
- Do not stop until the task is truly done
${compilePatterns}
Original task:
${state.prompt}`
}

function buildVerificationPrompt(state) {
  const maxLabel = typeof state.max_iterations === 'number' ? state.max_iterations : 'unbounded'
  const initPromise = state.initial_completion_promise || state.completion_promise
  return `ultrawork ─── ULTRAWORK LOOP VERIFICATION [${state.iteration}/${maxLabel}]

You already emitted <promise>${initPromise}</promise>. This does NOT finish the loop yet.

REQUIRED NOW:
- Call Oracle using delegate_task(agent="Oracle", task="Verify whether the original task is actually complete...")
- Ask Oracle to verify whether the original task is actually complete
- Include the original task in the Oracle request
- Explicitly tell Oracle to review skeptically and critically, and to look for reasons the task may still be incomplete or wrong
- If Oracle does not verify (does not output <promise>VERIFIED</promise>), continue fixing the task and do not consider it complete
- Only output <promise>VERIFIED</promise> YOURSELF after Oracle has confirmed the task is complete

Original task:
${state.prompt}`
}

function buildVerificationFailurePrompt(state) {
  const maxLabel = typeof state.max_iterations === 'number' ? state.max_iterations : 'unbounded'
  return `ultrawork ─── ULTRAWORK LOOP VERIFICATION FAILED [${state.iteration}/${maxLabel}]

Oracle did not emit <promise>VERIFIED</promise>. Verification failed.

REQUIRED NOW:
- Verification failed. Fix the task until Oracle's review is satisfied
- Oracle does not lie. Treat the verification result as ground truth
- Do not claim completion early or argue with the failed verification
- After fixing the remaining issues, request Oracle review again using delegate_task
- Only when the work is ready for review again, output: <promise>${state.completion_promise}</promise>

Original task:
${state.prompt}`
}

// ─── PLUGIN ────────────────────────────────────────────────────────────

export const RalphAutoloopPlugin = async ({ project, client, $, directory, worktree }) => {
  log(`init: dir=${directory}`)
  ensureStateDir()

  return {
    // ─── HOOK: session.created ──────────────────────────────────────
    "session.created": async (input) => {
      try {
        const sid = input?.sessionID || input?.id || ''
        if (!sid) return

        // Register in shared session registry (cross-plugin identity propagation)
        registry.handleSessionCreated(input)

        log(`session.created: ${sid}`)
      } catch (e) {
        log(`session.created error: ${e.message}`)
      }
    },

    // ─── HOOK: message.updated — MAIN LOOP TICK ─────────────────────
    // Fires every time the model produces a response.
    // This is our loop tick:
    //   1. Check for active loop matching this session
    //   2. Detect <promise>TAG</promise> in message
    //   3. Handle based on mode (normal vs ultrawork verification)
    //   4. Or inject continuation prompt to keep the loop going
    "message.updated": async (input, output) => {
      try {
        const msg = input?.message || input
        const sid = msg?.sessionID || msg?.session_id || input?.id || ''
        if (!sid) return

        // Recover active loop state from frontmatter .md (survives restarts)
        const state = loadState()
        if (!state) return
        if (state.session_id && state.session_id !== sid) return

        // Extract assistant text from the new message
        const text = msg?.parts?.map(p => p.text || '').join(' ') || ''
        if (!text) return

        log(`message.updated: sid=${sid.slice(0,12)}, it=${state.iteration}/${state.max_iterations || '∞'}`)

        // ═══════════════════════════════════════════════════════════════
        // PHASE 1: ULTRAWORK VERIFICATION CHECK
        // ═══════════════════════════════════════════════════════════════
        if (state.verification_pending) {
          // Check if VERIFIED promise appeared in this response
          if (detectPromiseInText(text, ULTRAWORK_VERIFICATION_PROMISE)) {
            log(`VERIFIED detected — ultrawork loop complete!`)
            clearState()
            await notify(client, {
              title: '🎯 ULTRAWORK LOOP COMPLETE!',
              message: `JUST ULW ULW! Task completed after ${state.iteration} iteration(s)`,
              variant: 'success', duration: 5000
            })
            return
          }

          // Verification still pending — check max iterations
          if (typeof state.max_iterations === 'number' && state.iteration >= state.max_iterations) {
            log(`Max iterations (${state.max_iterations}) reached without verification`)
            clearState()
            await notify(client, {
              title: '⏹ Ultrawork Loop Stopped (Max)',
              message: `${state.max_iterations} iterations without Oracle verification`,
              variant: 'warning', duration: 5000
            })
            return
          }

          // Inject verification FAILURE prompt first
          const failPrompt = buildVerificationFailurePrompt(state)
          await client.session.promptAsync({
            path: { id: sid },
            body: { tools: { question: false }, parts: [{ type: 'text', text: failPrompt }] },
            query: { directory }
          })

          // Only increment and save after successful injection
          state.iteration += 1
          state.started_at = new Date().toISOString()
          state.completion_promise = state.initial_completion_promise || DEFAULT_COMPLETION_PROMISE
          state.verification_pending = undefined
          saveState(state)

          await notify(client, {
            title: 'ULTRAWORK LOOP',
            message: 'Oracle verification failed. Continuing loop.',
            variant: 'warning', duration: 5000
          })
          return
        }

        // ═══════════════════════════════════════════════════════════════
        // PHASE 2: COMPLETION PROMISE DETECTION
        // ═══════════════════════════════════════════════════════════════
        if (detectPromiseInText(text, state.completion_promise)) {
          log(`Promise "${state.completion_promise}" detected in ${sid}`)

          // Ultrawork mode: DONE → transition to verification phase
          if (state.ultrawork) {
            state.verification_pending = true
            state.initial_completion_promise = state.initial_completion_promise || state.completion_promise
            state.completion_promise = ULTRAWORK_VERIFICATION_PROMISE
            saveState(state)

            const vPrompt = buildVerificationPrompt(state)
            await client.session.promptAsync({
              path: { id: sid },
              body: { tools: { question: false }, parts: [{ type: 'text', text: vPrompt }] },
              query: { directory }
            }).catch(e => log(`promptAsync failed: ${e.message}`))

            await notify(client, {
              title: 'ULTRAWORK LOOP',
              message: 'DONE detected. Oracle verification is now required.',
              variant: 'info', duration: 5000
            })
            return
          }

          // Normal mode: DONE → loop complete
          clearState()
          await notify(client, {
            title: '🎯 Ralph Loop Complete!',
            message: `Task completed after ${state.iteration} iteration(s)`,
            variant: 'success', duration: 5000
          })
          return
        }

        // ═══════════════════════════════════════════════════════════════
        // PHASE 3: ITERATION CHECK & CONTINUATION INJECTION
        // ═══════════════════════════════════════════════════════════════

        // Check max iterations
        if (typeof state.max_iterations === 'number' && state.iteration >= state.max_iterations) {
          log(`Max iterations (${state.max_iterations}) reached — clearing`)
          clearState()
          await notify(client, {
            title: '⏹ Loop Stopped (Max)',
            message: `${state.max_iterations} iterations without completion promise`,
            variant: 'warning', duration: 5000
          })
          return
        }

        // Rate limit: max one injection per MIN_INJECTION_INTERVAL
        const lastTick = lastInjectionTime.get(sid) || 0
        if (Date.now() - lastTick < MIN_INJECTION_INTERVAL) return
        lastInjectionTime.set(sid, Date.now())

        log(`it=${state.iteration + 1}/${state.max_iterations || '∞'} — injecting continuation`)

        const contPrompt = buildContinuationPrompt(state)
        await client.session.promptAsync({
          path: { id: sid },
          body: { tools: { question: false }, parts: [{ type: 'text', text: contPrompt }] },
          query: { directory }
        })

        // Only increment and save after successful injection
        state.iteration += 1
        state.started_at = new Date().toISOString()
        saveState(state)

        await notify(client, {
          title: 'Ralph Loop',
          message: `Iteration ${state.iteration}/${typeof state.max_iterations === 'number' ? state.max_iterations : '∞'}`,
          variant: 'info', duration: 2000
        })
      } catch (e) {
        log(`message.updated error: ${e.message}`)
      }
    },

    // ─── HOOK: experimental.session.compacting — preserve loop context ──
    "experimental.session.compacting": async (input, output) => {
      try {
        const sid = input?.sessionID || input?.id || ''
        const state = loadState()
        if (state && (!state.session_id || state.session_id === sid)) {
          output.context.push(
            `\n## ACTIVE RALPH LOOP\n` +
            `- Iteration: ${state.iteration || 0}` +
            `${typeof state.max_iterations === 'number' ? `/${state.max_iterations}` : ' (unlimited)'}\n` +
            `- Promise: ${state.completion_promise || 'none'}\n` +
            `- Ultrawork: ${state.ultrawork ? 'yes' : 'no'}\n` +
            `- Verification Pending: ${state.verification_pending ? 'yes' : 'no'}\n` +
            `- Status: active`
          )
          log(`compacting: preserved loop for ${sid}`)
        }
        log(`compacting: session ${sid}`)
      } catch (e) {
        log(`compacting error: ${e.message}`)
      }
    },

    // ─── TOOLS ──────────────────────────────────────────────────────
    tool: {
      // ── call_omo_agent: fire-and-forget background agent ────────
      "call_omo_agent": {
        description: "Delegate a task to an agent in a background session. Creates child session with parentID for identity propagation.",
        args: {
          agent: { type: "string", description: "Target agent name (e.g. 'Hephaestus - Builder', 'Scalpel - Code Dissector')" },
          task: { type: "string", description: "Task description for the agent" },
          model: { type: "string", description: "Optional model override", default: "" },
        },
        execute: async (args, ctx) => {
          log(`call_omo_agent: agent=${args.agent}, task="${(args.task||"").slice(0,60)}"`)
          const agent = args.agent
          const task = args.task
          const parentSessionID = ctx.sessionID
          const parentDirectory = ctx.directory

          try {
            const createResult = await client.session.create({
              body: {
                parentID: parentSessionID,
                title: `[subagent] ${agent}: ${(task||"").slice(0,60)}`,
              },
              query: { directory: parentDirectory },
            })

            if (!createResult?.data?.id) {
              return `❌ Failed to create background session: ${JSON.stringify(createResult?.error || "no id")}`
            }

            const sessionID = createResult.data.id
            log(`child session created: ${sessionID} (parent: ${parentSessionID})`)

            registry.register(sessionID, { agent, title: `[subagent] ${agent}: ${(task||"").slice(0,60)}`, parentID: parentSessionID })

            const promptBody = {
              agent: agent,
              tools: { question: false },
              parts: [{ type: "text", text: `⏣ **Delegated Task**\n\n${task}\n\nWork autonomously. Report results when done.` }]
            }
            if (args.model) promptBody.model = { providerID: "opencode", modelID: args.model }

            client.session.promptAsync({
              path: { id: sessionID },
              body: promptBody,
              query: { directory: parentDirectory },
            }).catch(e => log(`call_omo_agent prompt error: ${e.message}`))

            return `✅ Spawned ${agent} in session ${sessionID.slice(0,12)}... (parent: ${parentSessionID.slice(0,12)}...)`
          } catch (e) {
            log(`call_omo_agent error: ${e.message}`)
            return `❌ call_omo_agent failed: ${e.message}`
          }
        }
      },

      // ── delegate_task: sync — blocks until result ──────────────
      "delegate_task": {
        description: "Delegate a task to an agent and WAIT for the result. Blocks current session until subtask completes.",
        args: {
          agent: { type: "string", description: "Target agent name" },
          task: { type: "string", description: "Task description" },
          timeout: { type: "number", description: "Max wait seconds", default: 120 },
        },
        execute: async (args, ctx) => {
          log(`delegate_task: agent=${args.agent}, task="${(args.task||"").slice(0,60)}"`)
          const agent = args.agent
          const task = args.task
          const timeout = (args.timeout || 120) * 1000
          const parentSessionID = ctx.sessionID
          const parentDirectory = ctx.directory

          try {
            const createResult = await client.session.create({
              body: { parentID: parentSessionID, title: `[sync] ${agent}: ${(task||"").slice(0,60)}` },
              query: { directory: parentDirectory },
            })
            if (!createResult?.data?.id) {
              return `❌ Failed to create session: ${JSON.stringify(createResult?.error || "no id")}`
            }
            const sessionID = createResult.data.id
            log(`delegate session: ${sessionID}`)

            // Register in shared session registry for cross-plugin identity
            registry.register(sessionID, { agent, title: `[sync] ${agent}: ${(task||"").slice(0,60)}`, parentID: parentSessionID })

            await client.session.promptAsync({
              path: { id: sessionID },
              body: {
                agent: agent,
                tools: { question: false },
                parts: [{ type: "text", text: `⏣ **Task**\n\n${task}\n\nComplete this task and provide a summary.` }]
              },
              query: { directory: parentDirectory },
            })

            // Poll for completion
            const start = Date.now()
            let lastMsgCount = 0
            let stablePolls = 0

            while (Date.now() - start < timeout) {
              await new Promise(r => setTimeout(r, 2000))

              try {
                const msgs = await client.session.messages({ path: { id: sessionID } })
                const parts = msgs?.data?.parts || msgs?.parts || []
                const msgCount = parts.length

                if (msgCount > lastMsgCount) {
                  lastMsgCount = msgCount
                  stablePolls = 0
                } else {
                  stablePolls++
                }

                if (stablePolls >= 3 && lastMsgCount > 0) {
                  const lastText = parts.filter(p => p.type === "text").map(p => p.text || "").join("\n")
                  log(`delegate_task complete: ${sessionID} (${msgCount} messages)`)
                  return `✅ **${agent} result:**\n${lastText.slice(0, 5000)}`
                }
              } catch (e) {
                log(`delegate_task poll error: ${e.message}`)
              }
            }

            return `⚠️ delegate_task timed out after ${timeout/1000}s — session ${sessionID.slice(0,12)}...`
          } catch (e) {
            log(`delegate_task error: ${e.message}`)
            return `❌ delegate_task failed: ${e.message}`
          }
        }
      },

      // ── tui_notify: send toast notification ─────────────────────
      "tui_notify": {
        description: "Send a TUI notification/toast.",
        args: {
          title: { type: "string", description: "Notification title" },
          message: { type: "string", description: "Message body" },
          variant: { type: "string", description: "info, success, warning, or error", default: "info" },
          duration: { type: "number", description: "Milliseconds", default: 3000 },
        },
        execute: async (args) => {
          await notify(client, {
            title: args.title, message: args.message,
            variant: args.variant || "info", duration: args.duration || 3000,
          })
          return `✅ Notification sent: "${args.title}"`
        }
      },
    },
  }
}
