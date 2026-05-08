// Chat constants - separated for React Fast Refresh compatibility
export const CHAT_ACTIONS = {
  ADD_WINDOW: 'ADD_WINDOW',
  REMOVE_WINDOW: 'REMOVE_WINDOW',
  SET_ACTIVE_WINDOW: 'SET_ACTIVE_WINDOW',
  UPDATE_WINDOW: 'UPDATE_WINDOW',
  ADD_MESSAGE: 'ADD_MESSAGE',
  CLEAR_MESSAGES: 'CLEAR_MESSAGES',
  SET_MODELS: 'SET_MODELS',
  SET_TYPING: 'SET_TYPING',
  SET_CONNECTION: 'SET_CONNECTION',
  SET_SELECTED_MODEL: 'SET_SELECTED_MODEL',
  SET_AGENTS: 'SET_AGENTS',
  SET_SELECTED_AGENT: 'SET_SELECTED_AGENT',
  UPDATE_WINDOW_POSITION: 'UPDATE_WINDOW_POSITION',
  TOGGLE_WINDOW_MINIMIZED: 'TOGGLE_WINDOW_MINIMIZED',
  TOGGLE_WINDOW_MAXIMIZED: 'TOGGLE_WINDOW_MAXIMIZED',
}

// Available agents with emoji icons
export const DEFAULT_AGENTS = [
  { id: 'sisyphus', name: 'Sisyphus', emoji: '🜵' },
  { id: 'prometheus', name: 'Prometheus', emoji: '🔥' },
  { id: 'hephaestus', name: 'Hephaestus', emoji: '⚒️' },
  { id: 'oracle', name: 'Oracle', emoji: '🔮' },
]

export const CHAT_INITIAL_STATE = {
  windows: [],
  activeWindowId: null,
  availableModels: [],
  availableAgents: DEFAULT_AGENTS,
  globalTyping: false,
  connectionStatus: 'disconnected',
  selectedModel: 'llama3.2:3b',
  selectedAgent: 'sisyphus',
}
