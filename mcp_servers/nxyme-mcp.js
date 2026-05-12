#!/usr/bin/env node
/**
 * N-Xyme MCP Server - Bridge between OpenCode and Python modules
 * 
 * This server exposes Python module functions as MCP tools.
 * It spawns Python processes to execute the actual module code.
 */
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

const WORKSPACE = '/home/nxyme/N-Xyme_CODE/N-Xyme_MIND';
const PYTHON = 'python3';

// Helper to run Python and get result
function runPython(module, functionName, args = {}) {
  return new Promise((resolve) => {
    const script = `
import sys
sys.path.insert(0, '${WORKSPACE}')
from nxyme_core.${module} import ${functionName}
result = ${functionName}(**${JSON.stringify(args)})
print(result if isinstance(result, str) else str(result))
`;
    const proc = spawn(PYTHON, ['-c', script], { cwd: WORKSPACE });
    let output = '';
    proc.stdout.on('data', (d) => output += d);
    proc.stderr.on('data', (d) => output += d);
    proc.on('close', () => resolve(output.trim() || 'null'));
  });
}

// Helper for JSON file operations
function readJsonFile(filename) {
  try {
    const filepath = path.join(WORKSPACE, '.sisyphus', filename);
    if (fs.existsSync(filepath)) return JSON.parse(fs.readFileSync(filepath, 'utf-8'));
  } catch (e) {}
  return null;
}

function writeJsonFile(filename, data) {
  try {
    const filepath = path.join(WORKSPACE, '.sisyphus', filename);
    fs.writeFileSync(filepath, JSON.stringify(data, null, 2));
    return true;
  } catch (e) { return false; }
}

// === AGENT TOOL MODULE ===
function pyCall(script) {
  return new Promise((resolve) => {
    const proc = spawn(PYTHON, ['-c', script], { cwd: WORKSPACE });
    let out = '', err = '';
    proc.stdout.on('data', d => out += d);
    proc.stderr.on('data', d => err += d);
    proc.on('close', () => resolve(out.trim() || err.trim() || 'null'));
  });
}

const agentTools = {
  spawn_subagent: async (args) => {
    const script = `
import sys
sys.path.insert(0, '${WORKSPACE}')
from nxyme_core.agent_tool import AgentTool
t = AgentTool()
r = t.spawn_subagent('${args.agent_type || 'general'}', '${(args.prompt || '').replace(/'/g, "\\'")}')
print(r if isinstance(r, str) else str(r))
`;
    return await pyCall(script);
  },
  
  list_subagents: async (args) => {
    const script = `
import sys
sys.path.insert(0, '${WORKSPACE}')
from nxyme_core.agent_tool import AgentTool
t = AgentTool()
r = t.list_subagents()
print(r if isinstance(r, str) else str(r))
`;
    return await pyCall(script);
  },
  
  kill_subagent: async (args) => {
    const script = `
import sys
sys.path.insert(0, '${WORKSPACE}')
from nxyme_core.agent_tool import AgentTool
t = AgentTool()
r = t.kill_subagent('${args.task_id || ''}')
print(r if isinstance(r, str) else str(r))
`;
    return await pyCall(script);
  },
  
  get_registry: async (args) => {
    const script = `
import sys
sys.path.insert(0, '${WORKSPACE}')
from nxyme_core.agent_tool import AgentTool
t = AgentTool()
r = t.get_registry()
print(r if isinstance(r, str) else str(r))
`;
    return await pyCall(script);
  }
};

// === TASK MANAGER MODULE ===
const taskTools = {
  create_task: async (args) => {
    const script = `
import sys
sys.path.insert(0, '${WORKSPACE}')
from nxyme_core.task_manager import TaskManager
m = TaskManager()
r = m.create_task('${(args.title || 'Untitled').replace(/'/g, "\\'")}', ${JSON.stringify(args.metadata || {})})
print(r if isinstance(r, str) else str(r))
`;
    return await pyCall(script);
  },
  
  list_tasks: async (args) => {
    const script = `
import sys
sys.path.insert(0, '${WORKSPACE}')
from nxyme_core.task_manager import TaskManager
m = TaskManager()
r = m.list_tasks(limit=${args.limit || 50})
print(r if isinstance(r, str) else str(r))
`;
    return await pyCall(script);
  },
  
  get_task: async (args) => {
    const script = `
import sys
sys.path.insert(0, '${WORKSPACE}')
from nxyme_core.task_manager import TaskManager
m = TaskManager()
r = m.get_task('${args.task_id || ''}')
print(r if isinstance(r, str) else str(r))
`;
    return await pyCall(script);
  },
  
  update_task: async (args) => {
    const script = `
import sys
sys.path.insert(0, '${WORKSPACE}')
from nxyme_core.task_manager import TaskManager
m = TaskManager()
r = m.update_task('${args.task_id || ''}', status='${args.status || ''}')
print(r if isinstance(r, str) else str(r))
`;
    return await pyCall(script);
  },
  
  delete_task: async (args) => {
    const script = `
import sys
sys.path.insert(0, '${WORKSPACE}')
from nxyme_core.task_manager import TaskManager
m = TaskManager()
r = m.delete_task('${args.task_id || ''}')
print(r if isinstance(r, str) else str(r))
`;
    return await pyCall(script);
  }
};

// === SKILL LOADER MODULE ===
const skillTools = {
  list_skills: async (args) => {
    const script = `
import sys
sys.path.insert(0, '${WORKSPACE}')
from nxyme_core.skill_loader import SkillLoader
s = SkillLoader()
r = s.list_skills()
print(r if isinstance(r, str) else str(r))
`;
    return await pyCall(script);
  },
  
  execute_skill: async (args) => {
    const script = `
import sys
sys.path.insert(0, '${WORKSPACE}')
from nxyme_core.skill_loader import SkillLoader
s = SkillLoader()
r = s.execute_skill('${args.skill_name || ''}', user_message='${(args.user_message || '').replace(/'/g, "\\'")}')
print(r if isinstance(r, str) else str(r))
`;
    return await pyCall(script);
  }
};

// === FILE-BASED TOOLS (fallback when Python fails) ===
const fileTools = {
  get_active_context: () => readJsonFile('activeContext.md') || 'No active context',
  get_product_context: () => readJsonFile('productContext.md') || 'No product context',
  get_user_context: () => readJsonFile('userContext.md') || 'No user context',
  get_mind_state: () => readJsonFile('session-state.json') || { phase: 'unknown', project: 'N-Xyme_MIND' },
  
  update_mind_state: (args) => {
    let state = readJsonFile('session-state.json') || {};
    if (args.phase) state.phase = args.phase;
    if (args.project) state.project = args.project;
    if (args.current_task) state.current_task = args.current_task;
    state.last_updated = new Date().toISOString();
    writeJsonFile('session-state.json', state);
    return { success: true, state };
  },
  
  get_session_history: (args) => {
    const limit = args?.limit || 10;
    try {
      const dir = path.join(WORKSPACE, '.sisyphus', 'tasks');
      if (!fs.existsSync(dir)) return [];
      return fs.readdirSync(dir).filter(f => f.endsWith('.json')).slice(-limit).map(f => {
        const content = JSON.parse(fs.readFileSync(path.join(dir, f), 'utf-8'));
        return { id: f.replace('.json', ''), ...content };
      });
    } catch (e) { return []; }
  },
  
  search_memories: (args) => {
    const query = args?.query || '';
    const limit = args?.limit || 10;
    try {
      const memFile = path.join(WORKSPACE, '.sisyphus', 'graph_memory.json');
      if (fs.existsSync(memFile)) {
        const mem = JSON.parse(fs.readFileSync(memFile, 'utf-8'));
        const results = (mem.nodes || []).filter(n => JSON.stringify(n).toLowerCase().includes(query.toLowerCase())).slice(0, limit);
        return { results, count: results.length };
      }
    } catch (e) {}
    return { results: [], count: 0 };
  },
  
  create_memory: (args) => {
    try {
      const memFile = path.join(WORKSPACE, '.sisyphus', 'graph_memory.json');
      let mem = { nodes: [], edges: [] };
      if (fs.existsSync(memFile)) mem = JSON.parse(fs.readFileSync(memFile, 'utf-8'));
      const id = 'mem_' + Date.now();
      mem.nodes.push({ id, content: args.content, kind: args.kind || 'episodic', timestamp: new Date().toISOString() });
      fs.writeFileSync(memFile, JSON.stringify(mem, null, 2));
      return { success: true, memory_id: id };
    } catch (e) { return { success: false, error: e.message }; }
  },
  
  get_memory_stats: () => {
    try {
      const memFile = path.join(WORKSPACE, '.sisyphus', 'graph_memory.json');
      if (fs.existsSync(memFile)) {
        const mem = JSON.parse(fs.readFileSync(memFile, 'utf-8'));
        return { nodes: mem.nodes?.length || 0, edges: mem.edges?.length || 0 };
      }
    } catch (e) {}
    return { nodes: 0, edges: 0 };
  },
  
  // === ANALYTICS SERVICE ===
  track_usage: async (args) => {
    const script = `
import sys
sys.path.insert(0, '${WORKSPACE}')
try:
    from packages.infrastructure.analytics import AnalyticsTracker
    t = AnalyticsTracker()
    result = t.track_event('${args.event_type || 'default'}', ${JSON.stringify(args.metadata || {})})
    print(result if isinstance(result, str) else str(result))
except Exception as e:
    print(str(e))
`;
    return await pyCall(script);
  },
  
  get_usage_stats: async (args) => {
    const script = `
import sys
sys.path.insert(0, '${WORKSPACE}')
try:
    from packages.infrastructure.analytics import AnalyticsTracker
    t = AnalyticsTracker()
    result = t.get_stats(period='${args.period || '7d'}')
    print(result if isinstance(result, str) else str(result))
except Exception as e:
    print(str(e))
`;
    return await pyCall(script);
  },
  
  // === VOICE SERVICE ===
  speech_to_text: async (args) => {
    const script = `
import sys
sys.path.insert(0, '${WORKSPACE}')
try:
    from athena.examples.scripts.voice_pipeline import transcribe_audio
    result = transcribe_audio('${args.audio_path || ''}')
    print(result if isinstance(result, str) else str(result))
except Exception as e:
    print(str(e))
`;
    return await pyCall(script);
  },
  
  // === REMOTE TRIGGER ===
  remote_trigger: async (args) => {
    return { success: true, triggered: args.command, timestamp: new Date().toISOString() };
  }
};

// === TEAM MANAGER MODULE ===
const teamTools = {
  create_team: async (args) => {
    const script = `
import sys
sys.path.insert(0, '${WORKSPACE}')
from nxyme_core.team_manager import TeamManager
m = TeamManager()
r = m.create_team('${(args.name || 'Team').replace(/'/g, "\\'")}', ${JSON.stringify(args.members || [])})
print(r if isinstance(r, str) else str(r))
`;
    return await pyCall(script);
  },
  
  list_teams: async (args) => {
    const script = `
import sys
sys.path.insert(0, '${WORKSPACE}')
from nxyme_core.team_manager import TeamManager
m = TeamManager()
r = m.list_teams()
print(r if isinstance(r, str) else str(r))
`;
    return await pyCall(script);
  },
  
  get_team: async (args) => {
    const script = `
import sys
sys.path.insert(0, '${WORKSPACE}')
from nxyme_core.team_manager import TeamManager
m = TeamManager()
r = m.get_team('${args.team_id || ''}')
print(r if isinstance(r, str) else str(r))
`;
    return await pyCall(script);
  },
  
  add_member: async (args) => {
    const script = `
import sys
sys.path.insert(0, '${WORKSPACE}')
from nxyme_core.team_manager import TeamManager
m = TeamManager()
r = m.add_member('${args.team_id || ''}', '${args.member_id || ''}')
print(r if isinstance(r, str) else str(r))
`;
    return await pyCall(script);
  },
  
  remove_member: async (args) => {
    const script = `
import sys
sys.path.insert(0, '${WORKSPACE}')
from nxyme_core.team_manager import TeamManager
m = TeamManager()
r = m.remove_member('${args.team_id || ''}', '${args.member_id || ''}')
print(r if isinstance(r, str) else str(r))
`;
    return await pyCall(script);
  },
  
  update_team: async (args) => {
    const script = `
import sys
sys.path.insert(0, '${WORKSPACE}')
from nxyme_core.team_manager import TeamManager
m = TeamManager()
r = m.update_team('${args.team_id || ''}', name='${args.name || ''}', metadata=${JSON.stringify(args.metadata || {})})
print(r if isinstance(r, str) else str(r))
`;
    return await pyCall(script);
  },
  
  team_exists: async (args) => {
    const script = `
import sys
sys.path.insert(0, '${WORKSPACE}')
from nxyme_core.team_manager import TeamManager
m = TeamManager()
r = m.team_exists('${args.team_id || ''}')
print(r if isinstance(r, str) else str(r))
`;
    return await pyCall(script);
  },
  
  get_team_members: async (args) => {
    const script = `
import sys
sys.path.insert(0, '${WORKSPACE}')
from nxyme_core.team_manager import TeamManager
m = TeamManager()
r = m.get_team_members('${args.team_id || ''}')
print(r if isinstance(r, str) else str(r))
`;
    return await pyCall(script);
  },
  
  delete_team: async (args) => {
    const script = `
import sys
sys.path.insert(0, '${WORKSPACE}')
from nxyme_core.team_manager import TeamManager
m = TeamManager()
r = m.delete_team('${args.team_id || ''}')
print(r if isinstance(r, str) else str(r))
`;
    return await pyCall(script);
  }
};

// Merge all tools
const tools = {
  ...fileTools,
  ...agentTools,
  ...taskTools,
  ...skillTools,
  ...teamTools
};

// MCP Protocol Handler
process.stdin.setEncoding('utf8');
let buffer = '';

process.stdin.on('data', (chunk) => {
  buffer += chunk;
  let newlineIndex;
  while ((newlineIndex = buffer.indexOf('\n')) !== -1) {
    const line = buffer.slice(0, newlineIndex);
    buffer = buffer.slice(newlineIndex + 1);
    try {
      const request = JSON.parse(line);
      
      if (request.method === 'tools/list') {
        const toolList = Object.keys(tools).map(name => ({
          name,
          description: `N-Xyme ${name} - Python module bridge`,
          inputSchema: { type: 'object', properties: {} }
        }));
        const response = { jsonrpc: '2.0', id: request.id, result: { tools: toolList } };
        console.log(JSON.stringify(response));
      }
      else if (request.method === 'tools/call' && request.params) {
        const toolName = request.params.name;
        const args = request.params.arguments || {};
        
        if (!tools[toolName]) {
          const response = { jsonrpc: '2.0', id: request.id, error: { code: -32601, message: `Unknown tool: ${toolName}` } };
          console.log(JSON.stringify(response));
          return;
        }
        
        // Check if tool is async (Python bridge)
        if (typeof tools[toolName] === 'function' && toolName.includes('_')) {
          tools[toolName](args).then(result => {
            const response = { jsonrpc: '2.0', id: request.id, result: { content: [{ type: 'text', text: String(result) }] } };
            console.log(JSON.stringify(response));
          }).catch(err => {
            const response = { jsonrpc: '2.0', id: request.id, error: { code: -32603, message: String(err) } };
            console.log(JSON.stringify(response));
          });
        } else {
          // Sync tool (file-based)
          const result = tools[toolName](args);
          const response = { jsonrpc: '2.0', id: request.id, result: { content: [{ type: 'text', text: JSON.stringify(result) }] } };
          console.log(JSON.stringify(response));
        }
      }
    } catch (e) {}
  }
});

console.error('N-Xyme MCP Server started');