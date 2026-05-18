#!/usr/bin/env node
// Reads agents/{name}/agent.js → generates .opencode/agents/{name}.md
// ONE source of truth: the agent.js files. Everything else is generated.

import { readdirSync, readFileSync, writeFileSync, mkdirSync, existsSync } from 'fs'
import { join, dirname } from 'path'
import { fileURLToPath } from 'url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const root = join(__dirname, '..')
const agentsDir = join(root, 'agents')
const outDir = join(root, '.opencode/agents')
const modelsPath = join(root, 'config/nx_agents.json')

if (!existsSync(agentsDir)) { console.error('No agents/ directory found'); process.exit(1) }
mkdirSync(outDir, { recursive: true })

// Read model overrides from nx_agents.json if it exists
let modelOverrides = {}
let defaultModel = 'opencode/deepseek-v4-flash-free'
try {
  const nx = JSON.parse(readFileSync(modelsPath, 'utf8'))
  defaultModel = nx.default_model || defaultModel
  for (const a of nx.agents || []) {
    if (a.model) modelOverrides[a.name] = a.model
  }
} catch {}

const agentDirs = readdirSync(agentsDir, { withFileTypes: true })
let generated = 0

for (const entry of agentDirs) {
  if (!entry.isDirectory()) continue
  const agentFile = join(agentsDir, entry.name, 'agent.js')
  if (!existsSync(agentFile)) continue

  try {
    // Read raw agent.js — extract fields via regex (no import needed)
    const content = readFileSync(agentFile, 'utf8')
    const name = content.match(/name:\s*["'](.+?)["']/)?.[1] || entry.name
    const mode = content.match(/mode:\s*["'](.+?)["']/)?.[1] || 'all'
    const model = modelOverrides[name] || content.match(/model:\s*["'](.+?)["']/)?.[1] || defaultModel
    const description = content.match(/description:\s*["'](.+?)["']/)?.[1] || ''
    const color = content.match(/color:\s*["'](.+?)["']/)?.[1] || ''
    const skillsMatch = content.match(/skills:\s*\[([^\]]*)\]/)?.[1]
    const skills = skillsMatch ? skillsMatch.split(',').map(s => s.trim().replace(/["']/g, '')).filter(Boolean) : []

    // Extract prompt — everything between `prompt: \`\n and \n\``
    const promptMatch = content.match(/prompt:\s*`([\s\S]*?)`/)
    let prompt = promptMatch ? promptMatch[1].trim() : ''

    if (!prompt) {
      // Try single-quote string
      const sqMatch = content.match(/prompt:\s*'([\s\S]*?)'/)
      prompt = sqMatch ? sqMatch[1].trim() : ''
    }

    if (!name || !prompt) {
      console.warn(`  ⚠️  Skipping ${entry.name}: missing name or prompt`)
      continue
    }

    const sanitizedName = name.toLowerCase().replace(/[^a-z0-9]/g, '-').replace(/-+/g, '-')

    const md = `---
description: "${description.replace(/"/g, '\\"')}"
mode: ${mode}
model: ${model}
---

${prompt}
`
    writeFileSync(join(outDir, `${sanitizedName}.md`), md, 'utf8')
    generated++
    console.log(`  ✅ ${name}`)
  } catch (e) {
    console.warn(`  ⚠️  Error processing ${entry.name}: ${e.message}`)
  }
}

console.log(`\nGenerated ${generated} agents in .opencode/agents/`)
