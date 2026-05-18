# nx-agents Architecture

## Structure

```
nx-agents/
├── mcp/                          # Rust MCP server — lightweight tools
│   ├── Cargo.toml
│   └── src/main.rs               # ralph_start, reminders, sessions, welcome_back
│
├── plugin/                       # opencode plugin — registers agents
│   ├── package.json
│   ├── dist/index.js             # Auto-discovers features/
│   ├── features/
│   │   └── agent-injector.js     # Reads agents/*.js + config/models.json
│   └── agents/
│       ├── sisyphus.js           # Drop a .js file here to add an agent
│       ├── kairos.js
│       ├── mrwhite.js
│       └── ... (14 agents total)
│
└── config/
    └── models.json               # [Single source of truth] Which model each agent uses

~/.config/opencode/opencode.json  # Points to nx-agents/plugin and nx-agents/mcp binary
```

## How models work

**No recompile. No .ts files. One config file.**

1. `nx-agents/config/models.json` has `default_model` + `agent_overrides`
2. `agent-injector.js` reads it when opencode starts
3. Each agent gets its model: `override > agent.file.model > default_model`
4. Edit `models.json` → restart opencode → done

## How to add an agent

Drop a `.js` file in `plugin/agents/`:
```js
export default {
  name: "My Agent",
  mode: "subagent",
  color: "#FF0000",
  description: "What it does",
  prompt: `You are My Agent...`
}
```
It auto-inherits the default model from `config/models.json`. To override:
```js
export default {
  name: "My Agent",
  model: "gguf/qwen2.5-coder-7b-q4_k_m",  // optional override
  ...
}
```

## How model priority works

```
1. agent_overrides["My Agent"] in config/models.json   ← highest priority
2. agent.model in the .js file itself                   ← per-file override
3. default_model in config/models.json                  ← fallback
```
