/**
 * LSP Auto-Diagnose Plugin for OpenCode
 *
 * Hooks into tool.execute.after to check LSP health after file edits.
 * Periodically checks health every 60s.
 * Sends notifications on state changes.
 */

const path = require("path");
const { spawn } = require("child_process");

const DIAGNOSE_SCRIPT = path.join(__dirname, "diagnose.py");
const CHECK_INTERVAL_MS = 60 * 1000;

let previousState = {};
let intervalHandle = null;

function runDiagnose() {
  return new Promise((resolve, reject) => {
    const proc = spawn("python3", [DIAGNOSE_SCRIPT, "check"], {
      stdio: ["ignore", "pipe", "pipe"],
    });

    let stdout = "";
    let stderr = "";

    proc.stdout.on("data", (chunk) => {
      stdout += chunk.toString();
    });

    proc.stderr.on("data", (chunk) => {
      stderr += chunk.toString();
    });

    proc.on("error", reject);
    proc.on("close", (code) => {
      if (code !== 0) {
        reject(new Error("diagnose.py exited with code " + code + ": " + stderr));
        return;
      }
      try {
        const results = parseDiagnoseOutput(stdout);
        resolve(results);
      } catch (e) {
        reject(e);
      }
    });
  });
}

function parseDiagnoseOutput(stdout) {
  const results = [];
  const blocks = stdout.split(/\n\s*\n/);

  for (const block of blocks) {
    const trimmed = block.trim();
    if (!trimmed) continue;
    try {
      results.push(JSON.parse(trimmed));
    } catch (_) {
    }
  }

  return results;
}

function detectStateChanges(results) {
  const currentState = {};
  const changes = [];

  for (const r of results) {
    if (!r.server) continue;
    const status = r.action ? r.action : r.status;
    currentState[r.server] = status;

    if (previousState[r.server] && previousState[r.server] !== status) {
      changes.push({
        server: r.server,
        from: previousState[r.server],
        to: status,
      });
    }
  }

  previousState = currentState;
  return changes;
}

function notifyChanges(changes) {
  for (const change of changes) {
    const title = "LSP Status Change: " + change.server;
    const message = change.from + " -> " + change.to;

    try {
      spawn("notify-send", [title, message], {
        stdio: "ignore",
        detached: true,
      }).unref();
    } catch (_) {
    }
  }
}

async function checkHealth() {
  try {
    const results = await runDiagnose();
    const changes = detectStateChanges(results);
    if (changes.length > 0) {
      notifyChanges(changes);
    }
    return results;
  } catch (err) {
    console.error("[lsp-auto-diagnose] Health check failed:", err.message);
    return [];
  }
}

function startPeriodicCheck() {
  if (intervalHandle) return;
  intervalHandle = setInterval(checkHealth, CHECK_INTERVAL_MS);
  intervalHandle.unref();
}

function stopPeriodicCheck() {
  if (intervalHandle) {
    clearInterval(intervalHandle);
    intervalHandle = null;
  }
}

module.exports = {
  name: "lsp-auto-diagnose",
  version: "1.0.0",
  description: "LSP server health monitoring and auto-restart",

  hooks: {
    "tool.execute.after": async (context) => {
      const toolName = context.tool?.name || "";
      if (
        toolName.includes("write") ||
        toolName.includes("edit") ||
        toolName.includes("bash")
      ) {
        await checkHealth();
      }
    },

    "session.start": async () => {
      startPeriodicCheck();
    },

    "session.end": async () => {
      stopPeriodicCheck();
    },
  },

  commands: {
    "lsp-status": async () => {
      const results = await runDiagnose();
      const healthMap = {};
      for (const r of results) {
        if (r.server && !r.action) {
          healthMap[r.server] = r;
        }
      }
      return healthMap;
    },

    "lsp-diagnose": async () => {
      return checkHealth();
    },
  },
};
