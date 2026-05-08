import { useMemo, useState } from 'react'

/**
 * ChatMessage - Individual message rendering component
 * ADHD-friendly: Clear visual distinction between user/AI, code blocks with syntax highlighting
 */
function ChatMessage({ message, index, onRate }) {
  const { role, content, rating } = message
  
  const [isHovered, setIsHovered] = useState(false)
  
  const isUser = role === 'user'
  const isSystem = role === 'system'
  const isAssistant = role === 'assistant'
  const isError = content?.startsWith('Error:')
  
  // Parse code blocks
  const renderedContent = useMemo(() => {
    if (!content) return null
    
    // Check for code blocks (```language ... ```)
    const codeBlockRegex = /```(\w*)\n?([\s\S]*?)```/g
    const parts = []
    let lastIndex = 0
    let match
    
    while ((match = codeBlockRegex.exec(content)) !== null) {
      // Add text before code block
      if (match.index > lastIndex) {
        parts.push({
          type: 'text',
          content: content.slice(lastIndex, match.index)
        })
      }
      
      // Add code block
      parts.push({
        type: 'code',
        language: match[1] || 'text',
        content: match[2].trim()
      })
      
      lastIndex = match.index + match[0].length
    }
    
    // Add remaining text
    if (lastIndex < content.length) {
      parts.push({
        type: 'text',
        content: content.slice(lastIndex)
      })
    }
    
    return parts.length > 0 ? parts : [{ type: 'text', content }]
  }, [content])
  
  // Inline code detection
  const renderText = (text) => {
    const parts = text.split(/(`[^`]+`)/g)
    return parts.map((part, i) => {
      if (part.startsWith('`') && part.endsWith('`')) {
        return <code key={i} className="inline-code">{part.slice(1, -1)}</code>
      }
      // Handle URLs
      const urlRegex = /(https?:\/\/[^\s]+)/g
      const urlParts = part.split(urlRegex)
      return urlParts.map((urlPart, j) => {
        if (urlPart.match(urlRegex)) {
          return (
            <a 
              key={`${i}-${j}`} 
              href={urlPart} 
              target="_blank" 
              rel="noopener noreferrer"
              className="message-link"
            >
              {urlPart}
            </a>
          )
        }
        return urlPart
      })
    })
  }
  
  // Handle rating
  const handleRate = (ratingValue) => {
    if (onRate && isAssistant && !rating) {
      onRate(index, ratingValue)
    }
  }
  
  // Show rating buttons for assistant messages
  const showRatingButtons = isAssistant && (isHovered || rating)
  
  return (
    <div 
      className={`chat-message ${role} ${isError ? 'error' : ''}`}
      role="article"
      aria-label={`${role} message ${index + 1}`}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <div className="message-header">
        <span className="message-role">
          {isUser ? (
            <><span className="role-icon">👤</span> You</>
          ) : isSystem ? (
            <><span className="role-icon">⚙️</span> System</>
          ) : (
            <><span className="role-icon">🤖</span> AI</>
          )}
        </span>
        <span className="message-time">
          {new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </span>
      </div>
      
      <div className="message-content">
        {renderedContent?.map((part, i) => {
          if (part.type === 'code') {
            return (
              <div key={i} className="code-block">
                <div className="code-header">
                  <span className="code-language">{part.language || 'code'}</span>
                  <button 
                    className="copy-btn"
                    onClick={() => navigator.clipboard.writeText(part.content)}
                    aria-label="Copy code"
                  >
                    Copy
                  </button>
                </div>
                <pre><code>{part.content}</code></pre>
              </div>
            )
          }
          return (
            <p key={i} className="message-text">
              {renderText(part.content)}
            </p>
          )
        })}
      </div>
      
      {/* Rating buttons - only for assistant messages, show on hover or if rated */}
      {showRatingButtons && (
        <div className="message-rating">
          <button 
            className={`rating-btn thumbs-up ${rating === 'thumbsUp' ? 'active' : ''}`}
            onClick={() => handleRate('thumbsUp')}
            disabled={!!rating}
            aria-label="Rate thumbs up"
            title={rating ? 'You rated this positively' : 'Rate this message'}
          >
            👍
          </button>
          <button 
            className={`rating-btn thumbs-down ${rating === 'thumbsDown' ? 'active' : ''}`}
            onClick={() => handleRate('thumbsDown')}
            disabled={!!rating}
            aria-label="Rate thumbs down"
            title={rating ? 'You rated this negatively' : 'Rate this message'}
          >
            👎
          </button>
        </div>
      )}
    </div>
  )
}

export default ChatMessage
