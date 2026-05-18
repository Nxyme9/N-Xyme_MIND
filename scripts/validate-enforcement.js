#!/usr/bin/env node

/**
 * N-Xyme Enforcement Validation Script
 * 
 * Audits that all three enforcement layers agree before opencode launches.
 * Run by bins/nx before launching opencode.
 * 
 * Layer 1: agent.js permissions (extracted from file)
 * Layer 2: no-code-sisyphus plugin (NX_CODE_MODE logic)
 * Layer 3: generated .md files (YAML frontmatter permissions)
 */

const fs = require('fs');
const path = require('path');

const BASE_DIR = '/home/nxyme/N-Xyme_CODE/N-Xyme_MIND';
const AGENTS_DIR = path.join(BASE_DIR, 'agents');
const OPENCODE_DIR = path.join(BASE_DIR, '.opencode');
const PLUGINS_DIR = path.join(OPENCODE_DIR, 'plugins');
const MD_DIR = path.join(OPENCODE_DIR, 'agents');
const CONFIG_FILE = path.join(BASE_DIR, 'config/nx_agents.json');

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

function log(msg, type = 'info') {
  const prefix = type === 'error' ? '❌' : type === 'warn' ? '⚠️' : type === 'success' ? '✅' : 'ℹ️';
  console.error(`${prefix} ${msg}`);
}

function readJsonFile(filePath) {
  try {
    const content = fs.readFileSync(filePath, 'utf8');
    return JSON.parse(content);
  } catch (e) {
    return null;
  }
}

function extractYAMLFrontmatter(content) {
  const match = content.match(/^---\n([\s\S]*?)\n---/);
  if (!match) return {};
  
  const frontmatter = {};
  const lines = match[1].split('\n');
  let currentKey = null;
  let currentObj = null;
  
  for (const line of lines) {
    const indentMatch = line.match(/^(\s*)(.+)/);
    if (!indentMatch) continue;
    
    const indent = indentMatch[1].length;
    const value = indentMatch[2];
    
    if (indent === 0 && value.includes(':')) {
      const [key, ...rest] = value.split(':');
      const trimmedKey = key.trim();
      const trimmedValue = rest.join(':').trim();
      
      if (currentKey && currentObj) {
        frontmatter[currentKey] = currentObj;
      }
      
      if (trimmedValue === '' || trimmedValue === 'null' || trimmedValue === '~') {
        currentKey = trimmedKey;
        currentObj = {};
      } else {
        frontmatter[trimmedKey] = trimmedValue.replace(/^["']|["']$/g, '');
        currentKey = null;
        currentObj = null;
      }
    } else if (indent > 0 && currentObj !== null) {
      const [key, ...rest] = value.split(':');
      const trimmedKey = key.trim();
      const trimmedValue = rest.join(':').trim();
      
      if (trimmedKey) {
        if (trimmedValue === '') {
          currentObj[trimmedKey] = {};
        } else {
          currentObj[trimmedKey] = trimmedValue.replace(/^["']|["']$/g, '');
        }
      }
    }
  }
  
  if (currentKey && currentObj) {
    frontmatter[currentKey] = currentObj;
  }
  
  return frontmatter;
}

function extractAgentJsInfo(filePath) {
  try {
    const content = fs.readFileSync(filePath, 'utf8');
    
    // Extract name
    const nameMatch = content.match(/name:\s*["']([^"']+)["']/);
    const name = nameMatch ? nameMatch[1] : null;
    
    // Extract mode
    const modeMatch = content.match(/mode:\s*["']([^"']+)["']/);
    const mode = modeMatch ? modeMatch[1] : null;
    
    // Extract model
    const modelMatch = content.match(/model:\s*["']([^"']+)["']/);
    const model = modelMatch ? modelMatch[1] : null;
    
    // Extract skills
    const skillsMatch = content.match(/skills:\s*\[([^\]]+)\]/);
    const skills = skillsMatch ? skillsMatch[1].split(',').map(s => s.trim().replace(/"/g, '')) : [];
    
    // Extract permissions (if present)
    const permissionsMatch = content.match(/permissions:\s*\{([\s\S]*?)\n\s*\}/);
    let permissions = null;
    if (permissionsMatch) {
      // Simple parse of permissions object
      const permStr = permissionsMatch[1];
      permissions = {};
      
      // Edit permission
      const editMatch = permStr.match(/edit:\s*["']?([^"',\s]+)["']?/);
      if (editMatch) permissions.edit = editMatch[1];
      
      // Bash permission object
      const bashMatch = permStr.match(/bash:\s*\{([\s\S]*?)\}/);
      if (bashMatch) {
        permissions.bash = {};
        const bashContent = bashMatch[1];
        const bashLines = bashContent.split('\n');
        for (const bline of bashLines) {
          const bmatch = bline.match(/["'*]?([^"'*:\s]+)["'*]?:\s*["']?([^"',\s]+)["']?/);
          if (bmatch) {
            permissions.bash[bmatch[1]] = bmatch[2];
          }
        }
      }
    }
    
    return { name, mode, model, skills, permissions, filePath };
  } catch (e) {
    return { error: e.message, filePath };
  }
}

// ============================================================================
// MAIN VALIDATION
// ============================================================================

function validateEnforcement() {
  const gaps = [];
  const checked = {
    agents: 0,
    permissions: 0,
    plugins: 0,
    md_files: 0
  };
  
  // Step 1: Read all agent.js files
  log('Scanning agent.js files...');
  let agentJsFiles = [];
  try {
    const agentDirs = fs.readdirSync(AGENTS_DIR).filter(d => {
      return fs.statSync(path.join(AGENTS_DIR, d)).isDirectory();
    });
    
    for (const dir of agentDirs) {
      const agentFile = path.join(AGENTS_DIR, dir, 'agent.js');
      if (fs.existsSync(agentFile)) {
        const info = extractAgentJsInfo(agentFile);
        if (info.name) {
          agentJsFiles.push(info);
          checked.agents++;
        }
      }
    }
  } catch (e) {
    gaps.push({
      severity: 'fail',
      layer: 'agent.js',
      agent: 'system',
      description: `Failed to read agents directory: ${e.message}`
    });
  }
  
  // Step 2: Read all generated .md files
  log('Scanning generated .md files...');
  let mdFiles = [];
  try {
    if (fs.existsSync(MD_DIR)) {
      const mdFilenames = fs.readdirSync(MD_DIR).filter(f => f.endsWith('.md'));
      
      for (const filename of mdFilenames) {
        const mdPath = path.join(MD_DIR, filename);
        const content = fs.readFileSync(mdPath, 'utf8');
        const frontmatter = extractYAMLFrontmatter(content);
        
        if (frontmatter.permission) {
          mdFiles.push({
            filename,
            frontmatter,
            permissions: frontmatter.permission,
            mode: frontmatter.mode,
            model: frontmatter.model
          });
          checked.md_files++;
        }
      }
    }
  } catch (e) {
    gaps.push({
      severity: 'fail',
      layer: '.md',
      agent: 'system',
      description: `Failed to read .md files: ${e.message}`
    });
  }
  
  // Step 3: Read the plugin file
  log('Scanning plugin file...');
  let pluginInfo = null;
  const pluginPath = path.join(PLUGINS_DIR, 'no-code-sisyphus.js');
  if (fs.existsSync(pluginPath)) {
    const pluginContent = fs.readFileSync(pluginPath, 'utf8');
    pluginInfo = {
      path: pluginPath,
      content: pluginContent
    };
    checked.plugins++;
    
    // Check plugin logic
    const hasModeCheck = pluginContent.includes('NX_CODE_MODE');
    const hasAllMode = pluginContent.includes('all');
    const hasHephaestusMode = pluginContent.includes('hephaestus');
    const blocksWriteTools = pluginContent.includes('write') && 
                             pluginContent.includes('edit') && 
                             pluginContent.includes('apply_patch');
    
    if (!hasModeCheck) {
      gaps.push({
        severity: 'fail',
        layer: 'plugin',
        agent: 'system',
        description: 'Plugin does not check NX_CODE_MODE environment variable'
      });
    }
    
    if (!hasAllMode) {
      gaps.push({
        severity: 'warn',
        layer: 'plugin',
        agent: 'system',
        description: 'Plugin missing NX_CODE_MODE=all debug mode'
      });
    }
    
    if (!hasHephaestusMode) {
      gaps.push({
        severity: 'fail',
        layer: 'plugin',
        agent: 'system',
        description: 'Plugin missing NX_CODE_MODE=hephaestus exception'
      });
    }
    
    if (!blocksWriteTools) {
      gaps.push({
        severity: 'fail',
        layer: 'plugin',
        agent: 'system',
        description: 'Plugin does not block write/edit/apply_patch tools'
      });
    }
  } else {
    gaps.push({
      severity: 'fail',
      layer: 'plugin',
      agent: 'system',
      description: 'Plugin file not found: .opencode/plugins/no-code-sisyphus.js'
    });
  }
  
  // Step 4: Read config file for model overrides
  log('Checking config file...');
  const config = readJsonFile(CONFIG_FILE);
  
  // Step 5: Compare agent.js (Layer 1) vs .md (Layer 3)
  log('Comparing agent.js vs .md permissions...');
  
  for (const agentJs of agentJsFiles) {
    // Find matching .md file (by name)
    const jsName = agentJs.name || '';
    const matchingMd = mdFiles.find(md => {
      const mdName = md.filename.replace('.md', '').replace(/ - .*/, '').toLowerCase();
      const jsBaseName = jsName.split(' - ')[0].toLowerCase();
      return mdName.includes(jsBaseName) || jsBaseName.includes(mdName);
    });
    
    if (matchingMd) {
      // Check if permissions in agent.js match .md
      checked.permissions++;
      
      if (!agentJs.permissions && matchingMd.permissions) {
        gaps.push({
          severity: 'warn',
          layer: 'agent.js',
          agent: agentJs.name,
          description: 'agent.js missing permissions (only in .md file)'
        });
      }
      
      // Check edit permission consistency
      const jsEdit = agentJs.permissions?.edit;
      const mdEdit = matchingMd.permissions?.edit;
      
      if (jsEdit && mdEdit && jsEdit !== mdEdit) {
        gaps.push({
          severity: 'fail',
          layer: 'agent.js / .md',
          agent: agentJs.name,
          description: `edit permission mismatch: agent.js="${jsEdit}" vs .md="${mdEdit}"`
        });
      }
    } else {
      gaps.push({
        severity: 'warn',
        layer: 'agent.js / .md',
        agent: agentJs.name,
        description: 'No matching .md file found for agent'
      });
    }
  }
  
  // Step 6: Verify plugin coverage (Layer 2)
  log('Verifying plugin enforcement coverage...');
  
  // Identify agents that should be blocked (edit: deny)
  const blockedAgents = mdFiles.filter(md => md.permissions?.edit === 'deny');
  const allowedAgents = mdFiles.filter(md => md.permissions?.edit !== 'deny');
  
  // Check that orchestrator agents have edit: deny
  const orchestrators = agentJsFiles.filter(a => a.skills?.includes('no-code-sisyphus'));
  for (const orch of orchestrators) {
    const md = mdFiles.find(md => {
      const mdName = md.filename.replace('.md', '').replace(/ - .*/, '').toLowerCase();
      const jsBaseName = (orch.name || '').split(' - ')[0].toLowerCase();
      return mdName.includes(jsBaseName) || jsBaseName.includes(mdName);
    });
    
    if (md && md.permissions?.edit !== 'deny') {
      gaps.push({
        severity: 'fail',
        layer: 'agent.js / plugin',
        agent: orch.name,
        description: `Orchestrator agent missing edit:deny permission in .md`
      });
    }
  }
  
  // Check that Hephaestus has write access (no edit: deny)
  const hephaestus = mdFiles.find(md => md.filename.toLowerCase().includes('hephaestus'));
  if (hephaestus && hephaestus.permissions?.edit === 'deny') {
    gaps.push({
      severity: 'fail',
      layer: 'agent.js / plugin',
      agent: 'Hephaestus',
      description: 'Hephaestus should NOT have edit:deny (it needs to write code)'
    });
  }
  
  // Verify plugin allows Hephaestus when NX_CODE_MODE=hephaestus
  if (pluginInfo) {
    const pluginAllowsHephaestus = pluginInfo.content.includes('hephaestus');
    if (!pluginAllowsHephaestus) {
      gaps.push({
        severity: 'fail',
        layer: 'plugin',
        agent: 'Hephaestus',
        description: 'Plugin does not allow Hephaestus when NX_CODE_MODE=hephaestus'
      });
    }
  }
  
  // Check for agents missing from .md but should exist
  if (agentJsFiles.length !== mdFiles.length) {
    const jsNames = new Set(agentJsFiles.map(a => (a.name || '').split(' - ')[0].toLowerCase()));
    const mdNames = new Set(mdFiles.map(m => m.filename.replace('.md', '').replace(/ - .*/, '').toLowerCase()));
    
    const missingInMd = [...jsNames].filter(n => !mdNames.has(n));
    const extraInMd = [...mdNames].filter(n => !jsNames.has(n));
    
    if (missingInMd.length > 0) {
      gaps.push({
        severity: 'warn',
        layer: '.md',
        agent: 'sync',
        description: `Agents missing .md files: ${missingInMd.join(', ')}`
      });
    }
    
    if (extraInMd.length > 0) {
      gaps.push({
        severity: 'warn',
        layer: '.md',
        agent: 'sync',
        description: `Extra .md files without agent.js: ${extraInMd.join(', ')}`
      });
    }
  }
  
  // ============================================================================
  // OUTPUT RESULTS
  // ============================================================================
  
  const hasFailures = gaps.some(g => g.severity === 'fail');
  const hasWarnings = gaps.some(g => g.severity === 'warn');
  
  const result = {
    status: hasFailures ? 'fail' : hasWarnings ? 'warn' : 'pass',
    checked,
    gaps,
    summary: `${checked.agents} agents validated, ${gaps.filter(g => g.severity === 'fail').length} failures, ${gaps.filter(g => g.severity === 'warn').length} warnings`
  };
  
  // Output JSON to stdout
  console.log(JSON.stringify(result, null, 2));
  
  // Log summary to stderr
  if (result.status === 'pass') {
    log(result.summary, 'success');
  } else if (result.status === 'warn') {
    log(result.summary, 'warn');
  } else {
    log(result.summary, 'error');
  }
  
  // Log gaps details
  for (const gap of gaps) {
    log(`[${gap.layer}] ${gap.agent}: ${gap.description}`, gap.severity);
  }
  
  // Exit code
  process.exit(result.status === 'fail' ? 1 : 0);
}

// ============================================================================
// SCRIPT ENTRY POINT
// ============================================================================

try {
  validateEnforcement();
} catch (e) {
  console.error(JSON.stringify({
    status: 'fail',
    checked: { agents: 0, permissions: 0, plugins: 0, md_files: 0 },
    gaps: [{
      severity: 'fail',
      layer: 'system',
      agent: 'script',
      description: `Script error: ${e.message}`
    }],
    summary: 'Script crashed'
  }, null, 2));
  process.exit(1);
}
