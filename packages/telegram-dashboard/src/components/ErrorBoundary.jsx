import { Component } from 'react'

/**
 * Error Boundary Component
 * Catches JavaScript errors in child components and displays fallback UI
 * Follows React 19 best practices
 */
class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null, errorInfo: null }
  }

  // eslint-disable-next-line no-unused-vars
  static getDerivedStateFromError(_error) {
    return { hasError: true }
  }

  componentDidCatch(err, info) {
    console.error('ErrorBoundary caught an error:', err, info)
    this.setState({
      error: err,
      errorInfo: info,
    })
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null, errorInfo: null })
  }

  render() {
    if (this.state.hasError) {
      // Custom fallback UI or use props.fallback
      if (this.props.fallback) {
        return this.props.fallback({
          error: this.state.error,
          resetError: this.handleRetry,
        })
      }

      return (
        <div style={{
          padding: '20px',
          margin: '20px',
          background: 'rgba(239, 68, 68, 0.1)',
          border: '1px solid #ef4444',
          borderRadius: '8px',
          color: '#fca5a5',
        }}>
          <h2 style={{ margin: '0 0 10px', color: '#ef4444' }}>
            ⚠️ Something went wrong
          </h2>
          {this.state.error?.message && (
            <p style={{ margin: '0 0 15px', fontSize: '14px' }}>
              {this.state.error.message}
            </p>
          )}
          <button
            onClick={this.handleRetry}
            style={{
              padding: '8px 16px',
              background: '#3b82f6',
              border: 'none',
              borderRadius: '6px',
              color: 'white',
              cursor: 'pointer',
              fontSize: '14px',
            }}
          >
            Try Again
          </button>
        </div>
      )
    }

    return this.props.children
  }
}

export default ErrorBoundary
