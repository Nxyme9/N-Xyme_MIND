const API_BASE = 'http://localhost:8766'

/**
 * Fetch helper with error handling
 */
async function fetchAPI(endpoint, options = {}) {
  try {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    })
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }
    
    return await response.json()
  } catch (error) {
    console.error(`API Error [${endpoint}]:`, error.message)
    throw error
  }
}

/**
 * Registry API endpoints
 */
export const api = {
  // Agent registry
  getAgents: () => fetchAPI('/api/registry/agents'),
  
  // Tool registry
  getTools: () => fetchAPI('/api/registry/tools'),
  
  // Tool execution
  executeTool: (toolName, parameters = {}) => fetchAPI('/api/tools/execute', {
    method: 'POST',
    body: JSON.stringify({ tool: toolName, parameters })
  }),
  
  // Skill registry
  getSkills: () => fetchAPI('/api/registry/skills'),
  
  // Skill execution
  executeSkill: (skillId, parameters = {}) => fetchAPI('/api/skills/execute', {
    method: 'POST',
    body: JSON.stringify({ skill_id: skillId, parameters })
  }),
  
  // MCP registry
  getMcps: () => fetchAPI('/api/registry/mcps'),
  
  // MCP management
  startMcp: (name) => fetchAPI(`/api/mcps/${name}/start`, { method: 'POST' }),
  stopMcp: (name) => fetchAPI(`/api/mcps/${name}/stop`, { method: 'POST' }),
  getMcpStatus: (name) => fetchAPI(`/api/mcps/${name}/status`),
  
  // Discovery endpoint
  getDiscover: () => fetchAPI('/api/registry/discover'),
  
  // Learning progress
  getLearningProgress: () => fetchAPI('/api/learning/progress'),
  
  // Sessions
  getSessions: () => fetchAPI('/api/sessions/list'),
  getSession: (id) => fetchAPI(`/api/sessions/${id}`),
  
  // Settings
  getSettings: () => fetchAPI('/api/settings'),
  saveSettings: (settings) => fetchAPI('/api/settings', {
    method: 'POST',
    body: JSON.stringify(settings)
  }),
  
  // Models - GGUF local models
  getLocalModels: () => fetchAPI('/api/models/local'),
  
  // Models - Ollama (primary for chat)
  getOllamaModels: () => fetchAPI('/api/models/ollama'),
  
  // Model management
  loadModel: (modelName, backend) => fetchAPI('/api/models/load', {
    method: 'POST',
    body: JSON.stringify({ model_name: modelName, backend })
  }),
  getModelStatus: () => fetchAPI('/api/models/status'),
  
  // Routing stats
  getRoutingStats: () => fetchAPI('/api/routing/stats'),
  
  // Chat with Ollama via port 3000 proxy
  sendChatMessage: (message, model = 'llama3.2:3b', messages = [], agent = 'sisyphus') => {
    const chatMessages = messages.length > 0 
      ? [...messages, { role: 'user', content: message }]
      : [{ role: 'user', content: message }]
    
    return fetchAPI('/api/chat/completions', {
      method: 'POST',
      body: JSON.stringify({
        model: model,
        messages: chatMessages,
        stream: false,
        agent: agent  // Backend knows which agent handled the conversation
      })
    })
  },
  
  getChatModels: () => fetchAPI('/api/models/ollama'),
  
  // Memory API
  searchMemory: (query) => fetchAPI(`/api/memory/search?query=${encodeURIComponent(query)}`),
  writeMemory: (content, kind = 'episodic', scope = 'global') => fetchAPI('/api/memory/write', {
    method: 'POST',
    body: JSON.stringify({ content, kind, scope })
  }),
  recallSession: (sessionId) => fetchAPI(`/api/memory/recall?session_id=${sessionId}`),
  
  // Orchestration
  spawnAgent: (agent, task, context = {}) => fetchAPI('/api/orchestration/spawn', {
    method: 'POST',
    body: JSON.stringify({ agent, task, context })
  }),
  getTaskStatus: (taskId) => fetchAPI(`/api/orchestration/status/${taskId}`),
  
  // Health
  getHealth: () => fetchAPI('/api/health'),
  
  // Unified memory search
  unifiedSearch: (query, limit = 10) => fetchAPI(`/api/memory/unified/search?query=${encodeURIComponent(query)}&limit=${limit}`),
  
  // Message rating for learning
  sendMessageRating: (ratingData) => fetchAPI('/api/learning/rate-message', {
    method: 'POST',
    body: JSON.stringify(ratingData)
  }),
}

/**
 * Get Telegram user info if available
 */
export function getTelegramUser() {
  if (window.Telegram?.WebApp?.initDataUnsafe?.user) {
    return window.Telegram.WebApp.initDataUnsafe.user
  }
  return null
}

/**
 * Get Telegram WebApp instance
 */
export function getTelegramWebApp() {
  return window.Telegram?.WebApp || null
}

export default api
