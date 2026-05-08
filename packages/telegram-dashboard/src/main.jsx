import { StrictMode, useEffect } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import './index.css'
import App from './App.jsx'
import ErrorBoundary from './components/ErrorBoundary.jsx'

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      gcTime: 1000 * 60 * 30, // 30 minutes (formerly cacheTime)
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
})

export function TelegramInit() {
  useEffect(() => {
    // Initialize Telegram WebApp
    if (window.Telegram?.WebApp) {
      // Ready the app
      window.Telegram.WebApp.ready()
      
      // Set theme based on Telegram color scheme
      const colorScheme = window.Telegram.WebApp.colorScheme
      document.documentElement.setAttribute('data-theme', colorScheme)
      
      // Set viewport for mobile
      window.Telegram.WebApp.setHeaderColor('bg_color')
      window.Telegram.WebApp.setBackgroundColor('bg_color')
    } else {
      // Fallback for development without Telegram
      document.documentElement.setAttribute('data-theme', 'dark')
    }
  }, [])
  
  return null
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <ErrorBoundary>
        <TelegramInit />
        <App />
      </ErrorBoundary>
    </QueryClientProvider>
  </StrictMode>,
)