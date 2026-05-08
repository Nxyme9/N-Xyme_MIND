import { createContext, useReducer, useCallback } from 'react'
import { CHAT_ACTIONS, CHAT_INITIAL_STATE } from './ChatConstants'

// Initial state - imported from separate file for Fast Refresh
const initialState = CHAT_INITIAL_STATE

// Action types - imported from separate file for Fast Refresh
const Actions = CHAT_ACTIONS

// Reducer
function chatReducer(state, action) {
  switch (action.type) {
    case Actions.ADD_WINDOW:
      return {
        ...state,
        windows: [...state.windows, action.payload],
        activeWindowId: action.payload.id
      }
    
    case Actions.REMOVE_WINDOW: {
      const remaining = state.windows.filter(w => w.id !== action.payload)
      return {
        ...state,
        windows: remaining,
        activeWindowId: state.activeWindowId === action.payload 
          ? (remaining[0]?.id || null)
          : state.activeWindowId
      }
    }
    
    case Actions.SET_ACTIVE_WINDOW:
      return {
        ...state,
        activeWindowId: action.payload
      }
    
    case Actions.UPDATE_WINDOW:
      return {
        ...state,
        windows: state.windows.map(w => 
          w.id === action.payload.id ? { ...w, ...action.payload } : w
        )
      }
    
    case Actions.ADD_MESSAGE: {
      const { windowId, message } = action.payload
      return {
        ...state,
        windows: state.windows.map(w =>
          w.id === windowId
            ? { ...w, messages: [...w.messages, message] }
            : w
        )
      }
    }
    
    case Actions.CLEAR_MESSAGES:
      return {
        ...state,
        windows: state.windows.map(w =>
          w.id === action.payload
            ? { ...w, messages: [] }
            : w
        )
      }
    
    case Actions.SET_MODELS:
      return {
        ...state,
        availableModels: action.payload
      }
    
    case Actions.SET_AGENTS:
      return {
        ...state,
        availableAgents: action.payload
      }
    
    case Actions.SET_SELECTED_AGENT:
      return {
        ...state,
        selectedAgent: action.payload
      }
    
    case Actions.SET_TYPING:
      return {
        ...state,
        globalTyping: action.payload
      }
    
    case Actions.SET_CONNECTION:
      return {
        ...state,
        connectionStatus: action.payload
      }
    
    case Actions.SET_SELECTED_MODEL:
      return {
        ...state,
        selectedModel: action.payload
      }
    
    case Actions.UPDATE_WINDOW_POSITION:
      return {
        ...state,
        windows: state.windows.map(w =>
          w.id === action.payload.id
            ? { ...w, position: action.payload.position }
            : w
        )
      }
    
    case Actions.TOGGLE_WINDOW_MINIMIZED:
      return {
        ...state,
        windows: state.windows.map(w =>
          w.id === action.payload
            ? { ...w, minimized: !w.minimized }
            : w
        )
      }
    
    case Actions.TOGGLE_WINDOW_MAXIMIZED:
      return {
        ...state,
        windows: state.windows.map(w =>
          w.id === action.payload
            ? { ...w, maximized: !w.maximized }
            : w
        )
      }
    
    default:
      return state
  }
}

// Create context
const ChatContext = createContext(null)

// Provider component
export function ChatProvider({ children }) {
  const [state, dispatch] = useReducer(chatReducer, initialState)
  
  // Window management
  const createWindow = useCallback((title = 'New Chat') => {
    const id = `window-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
    const newWindow = {
      id,
      title,
      messages: [],
      model: state.selectedModel,
      agent: state.selectedAgent,
      position: { x: 50 + (state.windows.length * 30), y: 50 + (state.windows.length * 30) },
      size: { width: 500, height: 600 },
      zIndex: state.windows.length + 1,
      minimized: false,
      maximized: false,
    }
    dispatch({ type: Actions.ADD_WINDOW, payload: newWindow })
    return id
  }, [state.windows.length, state.selectedModel, state.selectedAgent])
  
  const removeWindow = useCallback((windowId) => {
    dispatch({ type: Actions.REMOVE_WINDOW, payload: windowId })
  }, [])
  
  const setActiveWindow = useCallback((windowId) => {
    dispatch({ type: Actions.SET_ACTIVE_WINDOW, payload: windowId })
    // Update z-index
    dispatch({
      type: Actions.UPDATE_WINDOW,
      payload: { id: windowId, zIndex: state.windows.length + 1 }
    })
  }, [state.windows.length])
  
  const updateWindow = useCallback((windowId, updates) => {
    dispatch({ type: Actions.UPDATE_WINDOW, payload: { id: windowId, ...updates } })
  }, [])
  
  // Message management
  const addMessage = useCallback((windowId, message) => {
    dispatch({ type: Actions.ADD_MESSAGE, payload: { windowId, message } })
  }, [])
  
  const clearMessages = useCallback((windowId) => {
    dispatch({ type: Actions.CLEAR_MESSAGES, payload: windowId })
  }, [])
  
  // Model management
  const setModels = useCallback((models) => {
    dispatch({ type: Actions.SET_MODELS, payload: models })
  }, [])
  
  const setAgents = useCallback((agents) => {
    dispatch({ type: Actions.SET_AGENTS, payload: agents })
  }, [])
  
  const setSelectedAgent = useCallback((agent) => {
    dispatch({ type: Actions.SET_SELECTED_AGENT, payload: agent })
    // Update all windows to use new agent
    state.windows.forEach(w => {
      dispatch({ type: Actions.UPDATE_WINDOW, payload: { id: w.id, agent } })
    })
  }, [state.windows])
  
  const setSelectedModel = useCallback((model) => {
    dispatch({ type: Actions.SET_SELECTED_MODEL, payload: model })
    // Update all windows to use new model
    state.windows.forEach(w => {
      dispatch({ type: Actions.UPDATE_WINDOW, payload: { id: w.id, model } })
    })
  }, [state.windows])
  
  // Connection state
  const setConnectionStatus = useCallback((status) => {
    dispatch({ type: Actions.SET_CONNECTION, payload: status })
  }, [])
  
  // Typing indicator
  const setTyping = useCallback((typing) => {
    dispatch({ type: Actions.SET_TYPING, payload: typing })
  }, [])
  
  // Window controls
  const toggleMinimized = useCallback((windowId) => {
    dispatch({ type: Actions.TOGGLE_WINDOW_MINIMIZED, payload: windowId })
  }, [])
  
  const toggleMaximized = useCallback((windowId) => {
    dispatch({ type: Actions.TOGGLE_WINDOW_MAXIMIZED, payload: windowId })
  }, [])
  
  const updateWindowPosition = useCallback((windowId, position) => {
    dispatch({ type: Actions.UPDATE_WINDOW_POSITION, payload: { id: windowId, position } })
  }, [])
  
  // Get active window
  const getActiveWindow = useCallback(() => {
    return state.windows.find(w => w.id === state.activeWindowId) || null
  }, [state.windows, state.activeWindowId])
  
  // Bring window to front
  const bringToFront = useCallback((windowId) => {
    const maxZ = Math.max(...state.windows.map(w => w.zIndex || 0), 0)
    dispatch({ type: Actions.UPDATE_WINDOW, payload: { id: windowId, zIndex: maxZ + 1 } })
  }, [state.windows])
  
  // Value object
  const value = {
    // State
    windows: state.windows,
    activeWindowId: state.activeWindowId,
    availableModels: state.availableModels,
    availableAgents: state.availableAgents,
    globalTyping: state.globalTyping,
    connectionStatus: state.connectionStatus,
    selectedModel: state.selectedModel,
    selectedAgent: state.selectedAgent,
    
    // Window actions
    createWindow,
    removeWindow,
    setActiveWindow,
    updateWindow,
    toggleMinimized,
    toggleMaximized,
    updateWindowPosition,
    bringToFront,
    getActiveWindow,
    
    // Message actions
    addMessage,
    clearMessages,
    
    // Model actions
    setModels,
    setSelectedModel,
    
    // Agent actions
    setAgents,
    setSelectedAgent,
    
    // Connection
    setConnectionStatus,
    setTyping,
  }
  
  return (
    <ChatContext.Provider value={value}>
      {children}
    </ChatContext.Provider>
  )
}

// Hook - moved to separate file for Fast Refresh compliance
// export function useChat() {
//   const context = useContext(ChatContext)
//   if (!context) {
//     throw new Error('useChat must be used within a ChatProvider')
//   }
//   return context
// }

export default ChatContext