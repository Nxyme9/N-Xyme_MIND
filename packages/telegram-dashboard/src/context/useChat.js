import { useContext } from 'react'
import ChatContext from './ChatContext'

/**
 * useChat - Hook to access chat context
 * Must be used within a ChatProvider
 */
export function useChat() {
  const context = useContext(ChatContext)
  if (!context) {
    throw new Error('useChat must be used within a ChatProvider')
  }
  return context
}

export default useChat
