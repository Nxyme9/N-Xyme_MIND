import { useState, useEffect, useCallback, useRef } from 'react'
import { useChat } from '../context/useChat'
import ChatHeader from './chat/ChatHeader'
import ChatHistory from './chat/ChatHistory'
import ChatInput from './chat/ChatInput'
import { api } from '../services/api'

/**
 * WindowManager - Multi-window chat system manager
 * ADHD-friendly: Drag & drop, keyboard navigation, clear focus states
 */
function WindowManager() {
  const {
    windows,
    activeWindowId,
    availableModels,
    availableAgents,
    connectionStatus,
    createWindow,
    removeWindow,
    setActiveWindow,
    updateWindow,
    addMessage,
    clearMessages,
    setModels,
    // setAgents, // unused - agents come from App.jsx via ChatContext
    setConnectionStatus,
    toggleMinimized,
    toggleMaximized,
    bringToFront,
  } = useChat()

  const [loading, setLoading] = useState({})
  const [renamingTabId, setRenamingTabId] = useState(null)
  const [renamingTabTitle, setRenamingTabTitle] = useState('')
  const renameInputRef = useRef(null)

  // Fetch available models on mount
  useEffect(() => {
    const fetchModels = async () => {
      setConnectionStatus('connecting')
      try {
        const data = await api.getChatModels()
        if (data.status === 'ok' && data.models) {
          setModels(data.models)
          setConnectionStatus('connected')
        } else {
          // Fallback models
          setModels(['llama3.2:3b', 'qwen2.5-coder:7b', 'deepseek-r1'])
          setConnectionStatus('connected')
        }
      } catch (err) {
        console.error('Failed to fetch models:', err)
        setModels(['llama3.2:3b', 'qwen2.5-coder:7b', 'deepseek-r1'])
        setConnectionStatus('connected')
      }
    }
    fetchModels()
  }, [setModels, setConnectionStatus])

  // Create initial window if none exist
  useEffect(() => {
    if (windows.length === 0) {
      createWindow('Chat')
    }
  }, [windows.length, createWindow])

  // Send message handler
  const handleSendMessage = useCallback(async (windowId, userMessage, model, agent) => {
    // Add user message
    addMessage(windowId, { 
      role: 'user', 
      content: userMessage,
      timestamp: Date.now(),
      agent: agent  // Track which agent handled this message
    })

    setLoading(prev => ({ ...prev, [windowId]: true }))

    try {
      // Get existing messages for context
      const window = windows.find(w => w.id === windowId)
      const contextMessages = window?.messages || []

      // Pass agent to API for backend to know which agent handled the conversation
      const response = await api.sendChatMessage(userMessage, model, contextMessages, agent)

      let content = ''
      if (response.choices && response.choices[0]?.message) {
        content = response.choices[0].message.content
      } else if (response.message?.content) {
        content = response.message.content
      } else if (response.response) {
        content = response.response
      } else if (response.content) {
        content = response.content
      } else {
        content = JSON.stringify(response)
      }

      addMessage(windowId, { 
        role: 'assistant', 
        content,
        timestamp: Date.now(),
        agent: agent  // Track which agent responded
      })
    } catch (err) {
      addMessage(windowId, { 
        role: 'assistant', 
        content: `Error: ${err.message}`,
        timestamp: Date.now(),
        agent: agent
      })
    } finally {
      setLoading(prev => ({ ...prev, [windowId]: false }))
    }
  }, [windows, addMessage])

  // Handle model change
  const handleModelChange = useCallback((windowId, newModel) => {
    updateWindow(windowId, { model: newModel })
  }, [updateWindow])

  // Handle agent change
  const handleAgentChange = useCallback((windowId, newAgent) => {
    updateWindow(windowId, { agent: newAgent })
  }, [updateWindow])

  // Handle title change (rename)
  const handleTitleChange = useCallback((windowId, newTitle) => {
    updateWindow(windowId, { title: newTitle })
  }, [updateWindow])

  // Handle tab rename
  const handleTabDoubleClick = useCallback((windowId, currentTitle) => {
    setRenamingTabId(windowId)
    setRenamingTabTitle(currentTitle)
  }, [])

  const handleTabRenameChange = useCallback((e) => {
    setRenamingTabTitle(e.target.value)
  }, [])

  const saveTabRename = useCallback((windowId) => {
    if (renamingTabTitle.trim() && renamingTabTitle !== windows.find(w => w.id === windowId)?.title) {
      updateWindow(windowId, { title: renamingTabTitle.trim() })
    }
    setRenamingTabId(null)
  }, [renamingTabTitle, updateWindow, windows])

  const cancelTabRename = useCallback(() => {
    setRenamingTabId(null)
    setRenamingTabTitle('')
  }, [])

  const handleTabRenameKeyDown = useCallback((e, windowId) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      saveTabRename(windowId)
    } else if (e.key === 'Escape') {
      e.preventDefault()
      cancelTabRename()
    }
  }, [saveTabRename, cancelTabRename])

  // Handle clear
  const handleClear = useCallback((windowId) => {
    clearMessages(windowId)
  }, [clearMessages])

  // Handle window focus
  const handleWindowFocus = useCallback((windowId) => {
    setActiveWindow(windowId)
    bringToFront(windowId)
  }, [setActiveWindow, bringToFront])

  // Helper: Check if user is typing in an input field
  const isInputFocused = useCallback(() => {
    const active = document.activeElement
    if (!active) return false
    
    const tagName = active.tagName.toLowerCase()
    const isInput = tagName === 'input' && !['button', 'submit', 'reset', 'checkbox', 'radio'].includes(active.type)
    const isTextarea = tagName === 'textarea'
    const isContentEditable = active.isContentEditable || active.getAttribute('contenteditable') === 'true'
    
    // Also check if user has selected text
    const hasSelection = (active.selectionStart !== undefined && active.selectionStart !== active.selectionEnd)
    
    return isInput || isTextarea || isContentEditable || hasSelection
  }, [])

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e) => {
      // Don't trigger shortcuts when typing in input fields
      if (isInputFocused()) return

      // Ctrl+N: New window
      if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
        e.preventDefault()
        createWindow(`Chat ${windows.length + 1}`)
      }
      
      // Ctrl+W: Close active window
      if ((e.ctrlKey || e.metaKey) && e.key === 'w') {
        e.preventDefault()
        if (activeWindowId && windows.length > 1) {
          removeWindow(activeWindowId)
        }
      }
      
      // Ctrl+Tab: Cycle through windows
      if ((e.ctrlKey || e.metaKey) && e.key === 'Tab') {
        e.preventDefault()
        const currentIndex = windows.findIndex(w => w.id === activeWindowId)
        const nextIndex = (currentIndex + 1) % windows.length
        setActiveWindow(windows[nextIndex].id)
      }
      
      // Ctrl+1-9: Switch to window N
      if ((e.ctrlKey || e.metaKey) && e.key >= '1' && e.key <= '9') {
        const index = parseInt(e.key) - 1
        if (windows[index]) {
          setActiveWindow(windows[index].id)
        }
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [windows, activeWindowId, createWindow, removeWindow, setActiveWindow])

  // Render window controls
  const renderWindowControls = (window) => (
    <ChatHeader
      window={window}
      availableModels={availableModels}
      availableAgents={availableAgents}
      onModelChange={(newModel) => handleModelChange(window.id, newModel)}
      onAgentChange={(newAgent) => handleAgentChange(window.id, newAgent)}
      onTitleChange={(newTitle) => handleTitleChange(window.id, newTitle)}
      onClear={() => handleClear(window.id)}
      onClose={() => removeWindow(window.id)}
      onMinimize={() => toggleMinimized(window.id)}
      onMaximize={() => toggleMaximized(window.id)}
      connectionStatus={connectionStatus}
    />
  )

  // Render window content
  const renderWindowContent = (window) => (
    <div className="window-content">
      <ChatHistory
        messages={window.messages || []}
        loading={loading[window.id] || false}
        model={window.model}
        autoScroll={window.id === activeWindowId}
      />
      <ChatInput
        windowId={window.id}
        model={window.model}
        agent={window.agent}
        onSendMessage={handleSendMessage}
        disabled={loading[window.id] || connectionStatus !== 'connected'}
      />
    </div>
  )

  // Render floating window
  const renderFloatingWindow = (window) => {
    if (window.minimized) {
      return (
        <div
          key={window.id}
          className="chat-window minimized"
          style={{
            left: window.position.x,
            top: window.position.y,
            zIndex: window.zIndex,
          }}
          onClick={() => handleWindowFocus(window.id)}
        >
          <div className="minimized-content">
            <span className="window-icon">💬</span>
            <span className="window-label">{window.title}</span>
            <span className="message-count">{window.messages?.length || 0}</span>
          </div>
        </div>
      )
    }

    return (
      <div
        key={window.id}
        className={`chat-window ${window.maximized ? 'maximized' : ''} ${window.id === activeWindowId ? 'active' : ''}`}
        style={{
          left: window.position.x,
          top: window.position.y,
          width: window.maximized ? '100%' : window.size.width,
          height: window.maximized ? '100%' : window.size.height,
          zIndex: window.zIndex,
        }}
        onMouseDown={() => handleWindowFocus(window.id)}
        role="region"
        aria-label={`Chat window: ${window.title}`}
      >
        {renderWindowControls(window)}
        {renderWindowContent(window)}
      </div>
    )
  }

  // Tab bar for window switching
  const renderTabBar = () => (
    <div className="window-tab-bar">
      <button 
        className="new-window-btn"
        onClick={() => createWindow(`Chat ${windows.length + 1}`)}
        title="New window (Ctrl+N)"
        aria-label="Create new chat window"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M12 5v14M5 12h14" />
        </svg>
      </button>
      
      <div className="tabs-container">
        {windows.map((window, index) => (
          <button
            key={window.id}
            className={`window-tab ${window.id === activeWindowId ? 'active' : ''} ${renamingTabId === window.id ? 'renaming' : ''}`}
            onClick={() => renamingTabId !== window.id && handleWindowFocus(window.id)}
            onDoubleClick={() => handleTabDoubleClick(window.id, window.title)}
            title={`${window.title} (Ctrl+${index + 1}) - double-click to rename`}
            aria-selected={window.id === activeWindowId}
            role="tab"
          >
            <span className="tab-icon">💬</span>
            {renamingTabId === window.id ? (
              <input
                ref={renameInputRef}
                type="text"
                className="tab-title-input"
                value={renamingTabTitle}
                onChange={handleTabRenameChange}
                onKeyDown={(e) => handleTabRenameKeyDown(e, window.id)}
                onBlur={() => saveTabRename(window.id)}
                onClick={(e) => e.stopPropagation()}
              />
            ) : (
              <span className="tab-title">{window.title}</span>
            )}
            {window.messages?.length > 0 && (
              <span className="tab-badge">{window.messages.length}</span>
            )}
            {windows.length > 1 && (
              <button
                className="tab-close"
                onClick={(e) => {
                  e.stopPropagation()
                  removeWindow(window.id)
                }}
                title="Close"
                aria-label={`Close ${window.title}`}
              >
                ×
              </button>
            )}
          </button>
        ))}
      </div>
    </div>
  )

  // Main render
  return (
    <div className="window-manager">
      {renderTabBar()}
      
      <div className="windows-container">
        {windows.map(window => renderFloatingWindow(window))}
      </div>
      
      {/* Keyboard shortcuts hint */}
      <div className="keyboard-hints">
        <span><kbd>Ctrl+N</kbd> New</span>
        <span><kbd>Ctrl+W</kbd> Close</span>
        <span><kbd>Ctrl+Tab</kbd> Switch</span>
        <span><kbd>Ctrl+1-9</kbd> Go to</span>
      </div>
    </div>
  )
}

export default WindowManager