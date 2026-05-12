import type { PluginInput } from "@opencode-ai/plugin";

export interface ToolInput {
  tool: string;
  sessionID: string;
  callID: string;
}

export interface BeforeOutput {
  args: Record<string, unknown>;
  message?: Record<string, unknown>;
}

export interface AfterOutput {
  title: string;
  output: string;
  metadata: unknown;
}

export interface HookConfig {
  maxLatencyMs: number;
  enableMemoryInjection: boolean;
  enableLearningLogging: boolean;
  enableRoutingHints: boolean;
  enableFingerprint: boolean;
  memoryBudget: number;
}

const DEFAULT_CONFIG: HookConfig = {
  maxLatencyMs: 800,
  enableMemoryInjection: true,
  enableLearningLogging: true,
  enableRoutingHints: true,
  enableFingerprint: true,
  memoryBudget: 500,
};

export function createNXBrainHook(_ctx: PluginInput, config: Partial<HookConfig> = {}) {
  const cfg = { ...DEFAULT_CONFIG, ...config };
  const startTime = Date.now();
  const py = `${process.cwd()}/.venv/bin/python`;
  const bridge = `${process.cwd()}/packages/nx-brain-hook/bridge.py`;

  async function bridgeCall(tool: string, args: Record<string, unknown>): Promise<unknown> {
    try {
      const { execSync } = require("child_process");
      const input = JSON.stringify({ tool, args });
      const out = execSync(`${py} ${bridge}`, {
        input,
        maxBuffer: 1024 * 1024,
        timeout: cfg.maxLatencyMs,
        encoding: "utf-8",
      });
      return JSON.parse(out);
    } catch {
      return null;
    }
  }

  return {
    async "tool.execute.before"(input: ToolInput, output: BeforeOutput) {
      const args = output.args || {};

      if (cfg.enableFingerprint) {
        const fp = await bridgeCall("fingerprint.inject_context", {
          agent: "atlas",
          task: String(args.description || args.prompt || ""),
        });
        if (fp && (fp as Record<string, unknown>)?.context) {
          output.message = output.message || {};
          (output.message as Record<string, unknown>).__nxFP = fp;
        }
      }

      if (cfg.enableMemoryInjection) {
        const mem = await bridgeCall("memory.search", {
          task: String(args.description || args.prompt || ""),
        });
        if (mem && (mem as Record<string, unknown>)?.context) {
          output.message = output.message || {};
          (output.message as Record<string, unknown>).__nxMem = (mem as Record<string, unknown>).context;
        }
      }

      if (cfg.enableRoutingHints && input.tool === "task") {
        const routing = await bridgeCall("learning.route_task", {
          task_description: String(args.description || args.prompt || ""),
        });
        if (routing) {
          output.message = output.message || {};
          (output.message as Record<string, unknown>).__nxRoute = routing;
        }
      }

      if (cfg.enableLearningLogging) {
        bridgeCall("learning.log_outcome", {
          task_id: input.callID,
          agent: input.tool,
          success: true,
          latency_ms: 0,
        });
      }
    },

    async "tool.execute.after"(input: ToolInput, output: AfterOutput) {
      if (cfg.enableLearningLogging) {
        bridgeCall("learning.log_outcome", {
          task_id: input.callID,
          agent: input.tool,
          success: !output.output.includes("error"),
          latency_ms: Date.now() - startTime,
        });
      }

      if (input.tool === "task") {
        bridgeCall("fingerprint.record_pattern", {
          pattern_type: "tool_sequence",
          outcome: JSON.stringify({ tool: input.tool, session: input.sessionID, ok: !output.output.includes("error") }),
        });
      }
    },

    async event(input: { event: { type: string; properties?: unknown } }) {
      if (input.event.type === "session.start" || input.event.type === "session.resume") {
        bridgeCall("fingerprint.inject_context", { agent: "atlas", task: "session_warmup" });
      }
    },
  };
}
