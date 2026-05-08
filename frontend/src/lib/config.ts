// Backend configuration - centralizes all backend URLs to prevent SSRF
export const config = {
  backend: {
    brainMcp: process.env.BACKEND_BRAIN_MCP || "http://localhost:8765",
    httpGateway: process.env.BACKEND_HTTP_GATEWAY || "http://localhost:8766",
    // Use httpGateway for orchestration APIs (8766 proxies to brain_mcp)
    orchestration: process.env.BACKEND_HTTP_GATEWAY || "http://localhost:8766",
    modelRouter: process.env.BACKEND_MODEL_ROUTER || "http://localhost:8000",
  },
  cors: {
    origins: process.env.CORS_ORIGINS?.split(",") || ["http://localhost:3000"],
  },
  rateLimit: {
    windowMs: parseInt(process.env.RATE_LIMIT_WINDOW || "60000"),
    maxRequests: parseInt(process.env.RATE_LIMIT_MAX || "100"),
  },
};

export function isAllowedOrigin(origin: string): boolean {
  return config.cors.origins.includes(origin) || 
         config.cors.origins.includes("*");
}