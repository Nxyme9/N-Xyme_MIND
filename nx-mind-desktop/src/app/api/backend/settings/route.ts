import { NextResponse } from "next/server";

export interface Settings {
  theme: "light" | "dark" | "system";
  language: string;
  autoSave: boolean;
  notifications: boolean;
  agentPollingInterval: number;
  mcpTimeout: number;
  maxRetries: number;
  defaultModel: string;
  routingStrategy: "auto" | "cost" | "quality" | "speed";
}

const DEFAULT_SETTINGS: Settings = {
  theme: "dark",
  language: "en",
  autoSave: true,
  notifications: true,
  agentPollingInterval: 5000,
  mcpTimeout: 3000,
  maxRetries: 3,
  defaultModel: "minimax-m2.5-free",
  routingStrategy: "auto",
};

interface SettingsResponse {
  settings: Settings;
  backendAvailable: boolean;
  timestamp: string;
}

interface SettingsSaveRequest {
  settings: Partial<Settings>;
}

export async function GET(): Promise<NextResponse<SettingsResponse>> {
  try {
    // Try to fetch settings from backend (nx-brain-mcp memory)
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 3000);

    try {
      // Call nx-brain-mcp to retrieve stored settings
      const response = await fetch("http://localhost:8765/memory_get", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ key: "user_settings" }),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (response.ok) {
        const data = await response.json();
        if (data.value && typeof data.value === "object") {
          return NextResponse.json({
            settings: { ...DEFAULT_SETTINGS, ...data.value },
            backendAvailable: true,
            timestamp: new Date().toISOString(),
          });
        }
      }
    } catch {
      clearTimeout(timeoutId);
    }

    // Return defaults if backend unavailable
    return NextResponse.json({
      settings: DEFAULT_SETTINGS,
      backendAvailable: false,
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error("Error fetching settings:", error);
    return NextResponse.json(
      {
        settings: DEFAULT_SETTINGS,
        backendAvailable: false,
        timestamp: new Date().toISOString(),
      },
      { status: 200 }
    );
  }
}

export async function POST(
  request: Request
): Promise<NextResponse<SettingsResponse>> {
  try {
    const body: SettingsSaveRequest = await request.json();

    if (!body.settings || typeof body.settings !== "object") {
      return NextResponse.json(
        {
          settings: DEFAULT_SETTINGS,
          backendAvailable: false,
          timestamp: new Date().toISOString(),
        },
        { status: 400 }
      );
    }

    // Validate settings keys
    const validKeys = Object.keys(DEFAULT_SETTINGS);
    const invalidKeys = Object.keys(body.settings).filter(
      (key) => !validKeys.includes(key)
    );

    if (invalidKeys.length > 0) {
      return NextResponse.json(
        {
          error: `Invalid settings keys: ${invalidKeys.join(", ")}`,
          settings: DEFAULT_SETTINGS,
          backendAvailable: false,
          timestamp: new Date().toISOString(),
        },
        { status: 400 }
      );
    }

    const mergedSettings = { ...DEFAULT_SETTINGS, ...body.settings };

    // Try to save to backend (nx-brain-mcp memory)
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 3000);

    try {
      const response = await fetch("http://localhost:8765/memory_write", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          key: "user_settings",
          value: mergedSettings,
        }),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (response.ok) {
        return NextResponse.json({
          settings: mergedSettings,
          backendAvailable: true,
          timestamp: new Date().toISOString(),
        });
      }
    } catch {
      clearTimeout(timeoutId);
    }

    // Return settings even if backend save failed
    return NextResponse.json({
      settings: mergedSettings,
      backendAvailable: false,
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error("Error saving settings:", error);
    return NextResponse.json(
      {
        settings: DEFAULT_SETTINGS,
        backendAvailable: false,
        timestamp: new Date().toISOString(),
      },
      { status: 500 }
    );
  }
}