import { useState, useEffect, useRef, useCallback } from 'react'
import { api } from '../services/api'
import ChatHeader from './chat/ChatHeader'
import ChatHistory from './chat/ChatHistory'
import ChatInput from './chat/ChatInput'

/**
 * Chat - Main chat component using modular sub-components
 * Refactored to use: ChatHeader, ChatHistory, ChatInput
 */
function Chat({ model: initialModel }) {
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(false)
  const [model, setModel] = useState(initialModel || 'llama3.2:3b')
  const [availableModels, setAvailableModels] = useState([])
  const [connectionStatus, setConnectionStatus] = useState('disconnected')
  const [error, setError] = useState(null)
  const messagesEndRef = useRef(null)

  // Get available models on mount
  useEffect(() => {
    setConnectionStatus('connecting')
    api.getChatModels()
      .then(data => {
        if (data.status === 'ok' && data.models) {
          setAvailableModels(data.models)
          setConnectionStatus('connected')
        } else {
          setAvailableModels(['llama3.2:3b', 'qwen2.5-coder:7b', 'deepseek-r1'])
          setConnectionStatus('connected')
        }
      })
      .catch(() => {
        setAvailableModels(['llama3.2:3b', 'qwen2.5-coder:7b', 'deepseek-r1'])
        setConnectionStatus('connected')
      })
  }, [])

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Send message handler
  const handleSendMessage = useCallback(async (userMessage, currentModel) => {
    if (!userMessage.trim() || loading) return

    const message = userMessage.trim()
    setLoading(true)
    setError(null)

    // Add user message immediately
    setMessages(prev => [...prev, { 
      role: 'user', 
      content: message,
      timestamp: Date.now()
    }])

    try {
      const response = await api.sendChatMessage(message, currentModel, messages)

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

      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content,
        timestamp: Date.now()
      }])
    } catch (err) {
      setError(err.message)
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: `Error: ${err.message}`,
        timestamp: Date.now()
      }])
    } finally {
      setLoading(false)
    }
  }, [loading, messages])

  // Handle model change
  const handleModelChange = useCallback((newModel) => {
    setModel(newModel)
  }, [])

  // Handle message rating
  const handleRateMessage = useCallback(async (index, rating) => {
    // Update local message state
    setMessages(prev => prev.map((msg, i) => 
      i === index ? { ...msg, rating } : msg
    ))
    
    // Send rating to backend for learning
    const msg = messages[index]
    if (msg) {
      try {
        await api.sendMessageRating({
          message_index: index,
          rating: rating,
          message_content: msg.content,
          role: msg.role,
          timestamp: msg.timestamp
        })
      } catch (err) {
        console.error('Failed to send rating:', err)
        // Rating is still stored locally even if API fails
      }
    }
  }, [messages])

  // Handle clear
  const handleClear = useCallback(() => {
    setMessages([])
    setError(null)
  }, [])

  return (
    <div className="chat-container">
      <ChatHeader
        window={{ title: 'AI Chat', model }}
        availableModels={availableModels}
        onModelChange={handleModelChange}
        onClear={handleClear}
        connectionStatus={connectionStatus}
      />
      
      <ChatHistory
        messages={messages}
        loading={loading}
        model={model}
        autoScroll={true}
        onRate={handleRateMessage}
      />
      
      <ChatInput
        windowId="main-chat"
        model={model}
        onSendMessage={(_, message, m) => handleSendMessage(message, m)}
        disabled={loading || connectionStatus !== 'connected'}
      />
      
      {error && (
        <div className="chat-error-banner">
          <span>{error}</span>
          <button onClick={() => setError(null)}>Dismiss</button>
        </div>
      )}
    </div>
  )
}

export default Chat