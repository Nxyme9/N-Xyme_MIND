import { useState, useCallback, useRef, useEffect } from 'react'

/**
 * ChatHeader - Window title, controls, context info
 * ADHD-friendly: Clear window controls, model indicator, connection status
 */
function ChatHeader({ 
  window, 
  availableModels = [], 
  availableAgents = [],
  onModelChange,
  onAgentChange,
  onTitleChange,
  onClear,
  onClose,
  onMinimize,
  onMaximize,
  connectionStatus = 'connected'
}) {
  const [showModelDropdown, setShowModelDropdown] = useState(false)
  const [showAgentDropdown, setShowAgentDropdown] = useState(false)
  const [isRenaming, setIsRenaming] = useState(false)
  const [editedTitle, setEditedTitle] = useState(window?.title || '')
  const inputRef = useRef(null)
  
  const model = window?.model || availableModels[0]?.name || 'llama3.2:3b'
  const agent = window?.agent || availableAgents[0]?.id || 'sisyphus'
  const agentData = availableAgents.find(a => a.id === agent) || { id: 'sisyphus', name: 'Sisyphus', emoji: '🜵' }
  
  // Connection status indicator
  const statusIndicator = {
    connected: { color: '#22c55e', label: 'Connected' },
    connecting: { color: '#f59e0b', label: 'Connecting...' },
    disconnected: { color: '#ef4444', label: 'Disconnected' },
    error: { color: '#ef4444', label: 'Error' },
  }[connectionStatus] || { color: '#6b7280', label: 'Unknown' }
  
  // Handle model selection
  const handleModelChange = useCallback((newModel) => {
    setShowModelDropdown(false)
    onModelChange?.(newModel)
  }, [onModelChange])
  
  // Handle agent selection
  const handleAgentChange = useCallback((newAgent) => {
    setShowAgentDropdown(false)
    onAgentChange?.(newAgent)
  }, [onAgentChange])

  // Handle title click - start renaming
  const handleTitleClick = useCallback(() => {
    setIsRenaming(true)
    setEditedTitle(window?.title || '')
  }, [window?.title])

  // Handle title change
  const handleTitleChange = useCallback((e) => {
    setEditedTitle(e.target.value)
  }, [])

  // Save new title
  const saveTitle = useCallback(() => {
    if (editedTitle.trim() && editedTitle !== window?.title) {
      onTitleChange?.(editedTitle.trim())
    }
    setIsRenaming(false)
  }, [editedTitle, window?.title, onTitleChange])

  // Cancel rename
  const cancelRename = useCallback(() => {
    setEditedTitle(window?.title || '')
    setIsRenaming(false)
  }, [window?.title])

  // Handle key events in rename input
  const handleRenameKeyDown = useCallback((e) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      saveTitle()
    } else if (e.key === 'Escape') {
      e.preventDefault()
      cancelRename()
    }
  }, [saveTitle, cancelRename])

  // Auto-focus input when renaming starts
  useEffect(() => {
    if (isRenaming && inputRef.current) {
      inputRef.current.focus()
      inputRef.current.select()
    }
  }, [isRenaming])
  
  // Keyboard shortcut for model switch (Ctrl+M)
  const handleKeyDown = useCallback((e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'm') {
      e.preventDefault()
      setShowModelDropdown(prev => !prev)
    }
  }, [])
  
  return (
    <div className="chat-header" onKeyDown={handleKeyDown}>
      {/* Window title */}
      <div className="header-left">
        {isRenaming ? (
          <input
            ref={inputRef}
            type="text"
            className="window-title-input"
            value={editedTitle}
            onChange={handleTitleChange}
            onKeyDown={handleRenameKeyDown}
            onBlur={saveTitle}
          />
        ) : (
          <h2 className="window-title" onClick={handleTitleClick} title="Click to rename">
            {window?.title || 'Chat'}
            <span className="rename-icon">✏️</span>
          </h2>
        )}
        <div className="connection-status">
          <span 
            className="status-dot" 
            style={{ backgroundColor: statusIndicator.color }}
            title={statusIndicator.label}
          />
          <span className="status-text">{statusIndicator.label}</span>
        </div>
      </div>
      
      {/* Model selector */}
      <div className="header-center">
        <div className="model-selector">
          <button 
            className="model-btn"
            onClick={() => setShowModelDropdown(!showModelDropdown)}
            aria-expanded={showModelDropdown}
            aria-haspopup="listbox"
          >
            <span className="model-icon">🧠</span>
            <span className="model-name">{model}</span>
            <span className={`dropdown-arrow ${showModelDropdown ? 'open' : ''}`}>▼</span>
          </button>
          
          {showModelDropdown && (
            <div className="model-dropdown" role="listbox">
              {availableModels.length > 0 ? (
                availableModels.map(m => (
                  <button
                    key={m.name || m}
                    className={`model-option ${model === (m.name || m) ? 'selected' : ''}`}
                    onClick={() => handleModelChange(m.name || m)}
                    role="option"
                    aria-selected={model === (m.name || m)}
                  >
                    <span className="option-name">{m.name || m}</span>
                    {m.size && <span className="option-size">{m.size}</span>}
                  </button>
                ))
              ) : (
                <div className="no-models">No models available</div>
              )}
            </div>
          )}
        </div>
      </div>
      
      {/* Window controls */}
      <div className="header-right">
        <button 
          className="header-btn clear-btn" 
          onClick={onClear}
          title="Clear chat (Ctrl+L)"
          aria-label="Clear chat"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
          </svg>
        </button>
        
        <button 
          className="header-btn minimize-btn" 
          onClick={onMinimize}
          title="Minimize"
          aria-label="Minimize window"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M5 12h14" />
          </svg>
        </button>
        
        <button 
          className="header-btn maximize-btn" 
          onClick={onMaximize}
          title="Maximize"
          aria-label="Maximize window"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
          </svg>
        </button>
        
        <button 
          className="header-btn close-btn" 
          onClick={onClose}
          title="Close (Ctrl+W)"
          aria-label="Close window"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
        </div>
        
        {/* Agent selector */}
        <div className="agent-selector">
          <button 
            className="model-btn agent-btn"
            onClick={() => setShowAgentDropdown(!showAgentDropdown)}
            aria-expanded={showAgentDropdown}
            aria-haspopup="listbox"
          >
            <span className="model-icon">{agentData.emoji}</span>
            <span className="model-name">{agentData.name}</span>
            <span className={`dropdown-arrow ${showAgentDropdown ? 'open' : ''}`}>▼</span>
          </button>
          
          {showAgentDropdown && (
            <div className="model-dropdown" role="listbox">
              {availableAgents.length > 0 ? (
                availableAgents.map(a => (
                  <button
                    key={a.id}
                    className={`model-option ${agent === a.id ? 'selected' : ''}`}
                    onClick={() => handleAgentChange(a.id)}
                    role="option"
                    aria-selected={agent === a.id}
                  >
                    <span className="option-icon">{a.emoji}</span>
                    <span className="option-name">{a.name}</span>
                  </button>
                ))
              ) : (
                <div className="no-models">No agents available</div>
              )}
            </div>
          )}
        </div>
      </div>
  )
}

export default ChatHeader