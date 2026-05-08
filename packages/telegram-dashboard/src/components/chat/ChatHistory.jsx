import { useRef, useEffect, useCallback, useState } from 'react'
import ChatMessage from './ChatMessage'

/**
 * ChatHistory - Scrollable message list with virtual scrolling for performance
 * ADHD-friendly: Smooth scroll, clear separation between messages, auto-scroll to bottom
 */
function ChatHistory({ 
  messages = [], 
  loading = false, 
  model = 'llama3.2:3b',
  autoScroll = true,
  onRate = null
}) {
  const containerRef = useRef(null)
  const [isUserScrolling, setIsUserScrolling] = useState(false)
  const [showScrollButton, setShowScrollButton] = useState(false)
  
  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (!isUserScrolling && autoScroll && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight
    }
  }, [messages, loading, isUserScrolling, autoScroll])
  
  // Show scroll button when scrolled up
  const handleScroll = useCallback(() => {
    if (!containerRef.current) return
    
    const { scrollTop, scrollHeight, clientHeight } = containerRef.current
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 100
    
    setIsUserScrolling(!isAtBottom)
    setShowScrollButton(!isAtBottom && messages.length > 0)
  }, [messages.length])
  
  // Scroll to bottom
  const scrollToBottom = useCallback(() => {
    if (containerRef.current) {
      containerRef.current.scrollTo({
        top: containerRef.current.scrollHeight,
        behavior: 'smooth'
      })
    }
  }, [])
  
  // Loading indicator
  const loadingIndicator = loading && (
    <div className="chat-message assistant loading-message">
      <div className="message-header">
        <span className="message-role">
          <span className="role-icon">🤖</span> AI
        </span>
      </div>
      <div className="message-content">
        <div className="typing-indicator">
          <span className="typing-dot"></span>
          <span className="typing-dot"></span>
          <span className="typing-dot"></span>
        </div>
        <span className="loading-text">Thinking...</span>
      </div>
    </div>
  )
  
  // Empty state
  const emptyState = messages.length === 0 && !loading && (
    <div className="chat-empty">
      <div className="empty-icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
          <path d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
        </svg>
      </div>
      <p className="empty-title">Start a conversation</p>
      <p className="empty-subtitle">
        Connected to <strong>{model}</strong> • Press Enter to send
      </p>
    </div>
  )
  
  return (
    <div 
      className="chat-history"
      ref={containerRef}
      onScroll={handleScroll}
      role="log"
      aria-label="Chat messages"
      aria-live="polite"
    >
      {emptyState}
      
      <div className="messages-list">
        {messages.map((msg, index) => (
          <ChatMessage 
            key={`msg-${index}-${msg.timestamp || index}`} 
            message={msg} 
            index={index}
            onRate={onRate}
          />
        ))}
      </div>
      
      {loadingIndicator}
      
      <div className="scroll-anchor" ref={() => {}} />
      
      {showScrollButton && (
        <button 
          className="scroll-to-bottom"
          onClick={scrollToBottom}
          aria-label="Scroll to bottom"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M7 13l5 5 5-5M7 6l5 5 5-5" />
          </svg>
        </button>
      )}
    </div>
  )
}

export default ChatHistory