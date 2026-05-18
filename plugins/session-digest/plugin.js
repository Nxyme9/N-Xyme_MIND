/**
 * Session Digest Plugin for OpenCode
 *
 * Hooks into session.end to auto-generate digest.
 * Provides /digest command to view last session's digest.
 * Hooks into experimental.chat.messages.transform to inject digest context on session start.
 */

const path = require("path");
const { spawn } = require("child_process");
const fs = require("fs");

const PLUGIN_DIR = __dirname;
const PARSER_SCRIPT = path.join(PLUGIN_DIR, "parser.py");
const GENERATOR_SCRIPT = path.join(PLUGIN_DIR, "generator.py");
const PROJECT_ROOT = path.resolve(PLUGIN_DIR, "../..");
const DIGEST_DIR = path.join(PROJECT_ROOT, "data", "sessions", "digests");

let lastSessionDigest = null;
let lastSessionId = null;

function runPython(script, args) {
  args = args || [];
  return new Promise(function(resolve, reject) {
    var proc = spawn("python3", [script].concat(args), {
      stdio: ["ignore", "pipe", "pipe"],
      cwd: PLUGIN_DIR,
    });

    var stdout = "";
    var stderr = "";

    proc.stdout.on("data", function(chunk) {
      stdout += chunk.toString();
    });

    proc.stderr.on("data", function(chunk) {
      stderr += chunk.toString();
    });

    proc.on("error", reject);
    proc.on("close", function(code) {
      if (code !== 0) {
        reject(new Error("Script exited with code " + code + ": " + stderr));
        return;
      }
      resolve({ stdout: stdout, stderr: stderr });
    });
  });
}

function generateDigest(sessionId) {
  var args = [];
  if (sessionId) {
    args.push("--session", sessionId);
  }
  return runPython(GENERATOR_SCRIPT, args);
}

function generateLatestDigest() {
  return runPython(GENERATOR_SCRIPT, ["--latest"]);
}

function readLatestDigest() {
  try {
    if (!fs.existsSync(DIGEST_DIR)) {
      return null;
    }

    var files = fs.readdirSync(DIGEST_DIR)
      .filter(function(f) { return f.endsWith(".md"); })
      .sort()
      .reverse();

    if (files.length === 0) {
      return null;
    }

    var latestFile = path.join(DIGEST_DIR, files[0]);
    return fs.readFileSync(latestFile, "utf-8");
  } catch (err) {
    console.error("[session-digest] Failed to read latest digest:", err.message);
    return null;
  }
}

function findLatestLogFile() {
  try {
    var logDir = path.join(
      require("os").homedir(),
      ".local",
      "share",
      "opencode",
      "log"
    );

    if (!fs.existsSync(logDir)) {
      return null;
    }

    var files = fs.readdirSync(logDir)
      .filter(function(f) { return f.endsWith(".log"); })
      .map(function(f) {
        return {
          name: f,
          path: path.join(logDir, f),
          mtime: fs.statSync(path.join(logDir, f)).mtimeMs,
        };
      })
      .sort(function(a, b) { return b.mtime - a.mtime; });

    return files.length > 0 ? files[0].path : null;
  } catch (err) {
    console.error("[session-digest] Failed to find latest log:", err.message);
    return null;
  }
}

module.exports = {
  name: "session-digest",
  version: "1.0.0",
  description: "Auto-generate session digests from OpenCode logs",

  hooks: {
    "session.end": async function(context) {
      try {
        var sessionId = (context && context.session && context.session.id) || (context && context.sessionId);
        console.error("[session-digest] Session ended, generating digest...");

        var result = await generateDigest(sessionId);

        if (result && result.stderr) {
          var filepathMatch = result.stderr.match(/Digest saved: (.+)/);
          if (filepathMatch) {
            lastSessionId = sessionId;
            lastSessionDigest = readLatestDigest();
            console.error("[session-digest] Digest generated: " + filepathMatch[1]);
          }
        }
      } catch (err) {
        console.error("[session-digest] Digest generation failed:", err.message);
      }
    },

    "session.start": async function(context) {
      try {
        var previousDigest = readLatestDigest();
        if (previousDigest) {
          console.error("[session-digest] Previous session digest loaded");
        }
      } catch (err) {
        console.error("[session-digest] Failed to load previous digest:", err.message);
      }
    },

    "experimental.chat.messages.transform": async function(context) {
      try {
        var messages = (context && context.messages) || [];

        if (messages.length <= 1) {
          var previousDigest = readLatestDigest();
          if (previousDigest) {
            var digestSummary = previousDigest
              .split("\n")
              .filter(function(line) { return line.startsWith("| **") || line.startsWith("- **"); })
              .slice(0, 10)
              .join("\n");

            var systemMessage = {
              role: "system",
              content: "Previous session digest summary:\n\n" + digestSummary + "\n\nUse this context to understand what was accomplished in the last session.",
            };

            messages.unshift(systemMessage);
          }
        }

        return { messages: messages };
      } catch (err) {
        console.error("[session-digest] Message transform failed:", err.message);
        return context;
      }
    },
  },

  commands: {
    digest: async function(args) {
      try {
        if (args && args.length > 0) {
          var sessionId = args[0];
          await generateDigest(sessionId);
        } else {
          await generateLatestDigest();
        }

        var digest = readLatestDigest();
        if (digest) {
          return digest;
        }
        return "No digest available. Run a session first or check logs exist.";
      } catch (err) {
        return "Digest generation failed: " + err.message;
      }
    },

    "digest-last": async function() {
      var digest = readLatestDigest();
      if (digest) {
        return digest;
      }
      return "No previous session digest found.";
    },

    "digest-list": async function() {
      try {
        if (!fs.existsSync(DIGEST_DIR)) {
          return "No digests directory found.";
        }

        var files = fs.readdirSync(DIGEST_DIR)
          .filter(function(f) { return f.endsWith(".md"); })
          .sort()
          .reverse();

        if (files.length === 0) {
          return "No digests generated yet.";
        }

        var lines = ["## Session Digests", ""];
        for (var i = 0; i < Math.min(files.length, 20); i++) {
          var file = files[i];
          var stat = fs.statSync(path.join(DIGEST_DIR, file));
          var date = stat.mtime.toISOString().split("T")[0];
          lines.push("- `" + file + "` (" + date + ")");
        }

        return lines.join("\n");
      } catch (err) {
        return "Failed to list digests: " + err.message;
      }
    },
  },
};
