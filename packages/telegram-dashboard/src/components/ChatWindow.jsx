import { useState, useEffect, useRef } from 'react'
import { api } from '../services/api'

function ChatWindow({ window: chatWindow, isActive, availableModels }) {
  const [messages, setMessages] = useState(chatWindow.messages || [])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const messagesEndRef = useRef(null)
  
  const model = chatWindow.model || availableModels[0]?.name || 'llama3.2:3b'

  // Scroll to bottom on new messages
  useEffect(() => {
    if (isActive && messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages, isActive])

  const sendMessage = async () => {
    if (!input.trim() || loading) return
    
    const userMessage = input.trim()
    setInput('')
    setLoading(true)
    setError(null)
    
    // Add user message immediately
    setMessages(prev => [...prev, { role: 'user', content: userMessage }])
    
    try {
      const response = await api.sendChatMessage(userMessage, model, messages)
      
      // Handle different response formats
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
      
      setMessages(prev => [...prev, { role: 'assistant', content }])
    } catch (err) {
      setError(err.message)
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: `Error: ${err.message}` 
      }])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  if (!isActive) return null

  return (
    <div className="chat-window">
      <div className="chat-messages">
        {messages.length === 0 && (
          <div className="chat-empty">
            <p>Send a message to start chatting</p>
            <p className="chat-hint">Model: {model}</p>
          </div>
        )}
        
        {messages.map((msg, index) => (
          <div key={index} className={`chat-message ${msg.role}`}>
            <div className="message-role">
              {msg.role === 'user' ? 'You' : 'AI'}
            </div>
            <div className="message-content">
              {msg.content}
            </div>
          </div>
        ))}
        
        {loading && (
          <div className="chat-message assistant">
            <div className="message-role">AI</div>
            <div className="message-content loading">
              <span className="typing-indicator">
                <span></span><span></span><span></span>
              </span>
              Thinking...
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>
      
      {error && (
        <div className="chat-error">
          <span>{error}</span>
          <button onClick={() => setError(null)}>×</button>
        </div>
      )}
      
      <div className="chat-input-container">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Type your message..."
          className="chat-input"
          rows={2}
          disabled={loading}
        />
        <button 
          onClick={sendMessage} 
          disabled={loading || !input.trim()}
          className="send-btn"
        >
          {loading ? '...' : 'Send'}
        </button>
      </div>
    </div>
  )
}

export default ChatWindow
