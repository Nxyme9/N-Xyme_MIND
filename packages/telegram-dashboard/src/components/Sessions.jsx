import { useState, useEffect } from 'react'
import { api } from '../services/api'

function Sessions({ onSessionChange }) {
  const [sessions, setSessions] = useState([])
  const [selectedSession, setSelectedSession] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    async function fetchSessions() {
      try {
        const result = await api.getSessions()
        if (result.status === 'ok' && result.data) {
          setSessions(result.data)
          if (result.data.length > 0) {
            setSelectedSession(result.data[0])
          }
        }
      } catch (err) {
        setError('Failed to load sessions')
        console.error(err)
      } finally {
        setLoading(false)
      }
    }
    fetchSessions()
  }, [])

  const handleSelectSession = (session) => {
    setSelectedSession(session)
    if (onSessionChange) {
      onSessionChange(session)
    }
  }

  if (loading) {
    return (
      <div className="sessions loading">
        <div className="spinner"></div>
        <p>Loading sessions...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="sessions error">
        <p>{error}</p>
        <button onClick={() => window.location.reload()}>Retry</button>
      </div>
    )
  }

  if (sessions.length === 0) {
    return (
      <div className="sessions empty">
        <p>No sessions found</p>
        <p className="hint">Start a new task to create a session</p>
      </div>
    )
  }

  return (
    <div className="sessions">
      <div className="sessions-header">
        <h3>Available Sessions</h3>
        <span className="session-count">{sessions.length} session{sessions.length !== 1 ? 's' : ''}</span>
      </div>
      
      <div className="sessions-list">
        {sessions.map((session) => (
          <div
            key={session.session_id || session.id || Math.random()}
            className={`session-card ${selectedSession?.session_id === session.session_id ? 'selected' : ''}`}
            onClick={() => handleSelectSession(session)}
          >
            <div className="session-info">
              <span className="session-id">
                {session.session_id?.substring(0, 12) || 'Current'}
              </span>
              <span className="session-status">
                {session.status || 'active'}
              </span>
            </div>
            {session.agent && (
              <span className="session-agent">{session.agent}</span>
            )}
            {session.last_updated && (
              <span className="session-date">
                {new Date(session.last_updated).toLocaleDateString()}
              </span>
            )}
          </div>
        ))}
      </div>
      
      {selectedSession && (
        <div className="session-details">
          <h4>Current Session</h4>
          <pre>{JSON.stringify(selectedSession, null, 2)}</pre>
        </div>
      )}
    </div>
  )
}

export default Sessions