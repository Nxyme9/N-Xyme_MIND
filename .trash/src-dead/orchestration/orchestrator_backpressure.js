// Lightweight backpressure utility for task orchestration
// Reads config/performance.json to decide whether to launch new tasks.
const fs = require('fs');
const path = require('path');

function loadConfig() {
  try {
    const raw = fs.readFileSync(path.resolve(__dirname, '../config/performance.json'), 'utf8');
    return JSON.parse(raw);
  } catch (e) {
    // Fallback defaults
    return {
      maxConcurrentTasks: 8,
      cpuUsageThresholdPercent: 85,
      cpuUsageWindowMs: 60000
    };
  }
}

function shouldLaunchNewTask(currentActive, cpuPercent) {
  const cfg = loadConfig();
  if (currentActive >= cfg.maxConcurrentTasks) {
    return false;
  }
  if (typeof cpuPercent === 'number' && cpuPercent >= cfg.cpuUsageThresholdPercent) {
    return false;
  }
  return true;
}

module.exports = { shouldLaunchNewTask };
