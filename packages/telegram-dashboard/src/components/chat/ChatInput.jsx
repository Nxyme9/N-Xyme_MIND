import { useState, useCallback, useRef, useEffect } from 'react'

/**
 * ChatInput - Message composition component
 * ADHD-friendly: Keyboard shortcuts, clear focus states, minimal friction
 */
function ChatInput({ 
  windowId, 
  model,
  agent,
  onSendMessage, 
  disabled = false,
  placeholder = 'Type your message...'
}) {
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const textareaRef = useRef(null)
  
  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 150) + 'px'
    }
  }, [input])
  
  // Focus textarea on mount
  useEffect(() => {
    textareaRef.current?.focus()
  }, [])
  
  const handleSend = useCallback(async () => {
    if (!input.trim() || sending || disabled) return
    
    const message = input.trim()
    setInput('')
    setSending(true)
    
    try {
      await onSendMessage(windowId, message, model, agent)
    } finally {
      setSending(false)
      // Refocus after send
      setTimeout(() => textareaRef.current?.focus(), 50)
    }
  }, [input, sending, disabled, windowId, model, agent, onSendMessage])
  
  // Keyboard shortcuts
  const handleKeyDown = useCallback((e) => {
    // Enter to send (without shift)
    if (e.key === 'Enter' && !e.shiftKey && !e.ctrlKey && !e.metaKey) {
      e.preventDefault()
      handleSend()
    }
    
    // Ctrl+Enter for new line (instead of send)
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault()
      const start = e.target.selectionStart
      const end = e.target.selectionEnd
      const newValue = input.slice(0, start) + '\n' + input.slice(end)
      setInput(newValue)
      // Set cursor position after the inserted newline
      setTimeout(() => {
        textareaRef.current.selectionStart = textareaRef.current.selectionEnd = start + 1
      }, 0)
    }
    
    // Escape to blur
    if (e.key === 'Escape') {
      textareaRef.current?.blur()
    }
    
    // Ctrl+K to clear input
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
      e.preventDefault()
      setInput('')
    }
  }, [handleSend, input])
  
  // Handle change
  const handleChange = useCallback((e) => {
    setInput(e.target.value)
  }, [])
  
  // Keyboard shortcut hints
  const shortcutHints = (
    <span className="input-hints">
      <kbd>Enter</kbd> send • <kbd>Ctrl+Enter</kbd> new line • <kbd>Ctrl+K</kbd> clear
    </span>
  )
  
  return (
    <div className="chat-input-wrapper">
      <div className="chat-input-container">
        <textarea
          ref={textareaRef}
          value={input}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          className="chat-input"
          rows={1}
          disabled={disabled || sending}
          aria-label="Chat message input"
        />
        <button
          onClick={handleSend}
          disabled={disabled || sending || !input.trim()}
          className={`send-btn ${sending ? 'sending' : ''}`}
          aria-label="Send message"
        >
          {sending ? (
            <span className="loading-dots">
              <span></span><span></span><span></span>
            </span>
          ) : (
            <svg viewBox="0 0 24 24" className="send-icon">
              <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" fill="currentColor"/>
            </svg>
          )}
        </button>
      </div>
      {shortcutHints}
    </div>
  )
}

export default ChatInput