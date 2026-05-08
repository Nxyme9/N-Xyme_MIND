import { useState } from 'react'
import { api } from '../services/api'

function McpStatus({ mcps, discover, onRefresh }) {
  const [loading, setLoading] = useState({})
  const [errors, setErrors] = useState({})
  const [mcpStatuses, setMcpStatuses] = useState({})

  const handleStartStop = async (mcpName, action) => {
    setLoading(prev => ({ ...prev, [mcpName]: true }))
    setErrors(prev => ({ ...prev, [mcpName]: null }))
    
    try {
      const method = action === 'start' ? 'startMcp' : 'stopMcp'
      const result = await api[method](mcpName)
      setMcpStatuses(prev => ({ ...prev, [mcpName]: result.status || (action === 'start' ? 'running' : 'stopped') }))
    } catch (error) {
      setErrors(prev => ({ ...prev, [mcpName]: error.message || `Failed to ${action} MCP` }))
    } finally {
      setLoading(prev => ({ ...prev, [mcpName]: false }))
    }
  }

  const getStatusClass = (mcp) => {
    if (mcpStatuses[mcp.name]) return mcpStatuses[mcp.name]
    return mcp.status || 'unknown'
  }

  const isCriticalMcp = (name) => {
    const criticalMcp = ['athena', 'memory', 'unified-memory', 'sequential-thinking', 'context7', 'filesystem']
    return criticalMcp.includes(name.toLowerCase())
  }

  const isLoading = (name) => loading[name]
  const getError = (name) => errors[name]

  return (
    <div className="mcp-status">
      <div className="section-header">
        <h2>MCP Configuration</h2>
        {onRefresh && (
          <button className="refresh-btn" onClick={onRefresh} title="Refresh MCP status">
            ↻
          </button>
        )}
      </div>

      <div className="mcp-list">
        {(!mcps || mcps.length === 0) ? (
          <p className="empty">No MCPs configured</p>
        ) : (
          mcps.map((mcp, index) => (
            <div key={mcp.name || index} className="mcp-item">
              <div className="mcp-header">
                <span className="mcp-name">{mcp.name || 'Unknown MCP'}</span>
                <span className={`status-dot ${getStatusClass(mcp)}`}></span>
              </div>
              
              {mcp.description && (
                <p className="mcp-desc">{mcp.description}</p>
              )}
              
              {mcp.tools && (
                <div className="mcp-tools">
                  {mcp.tools.map((tool, i) => (
                    <span key={i} className="tool-tag">{tool}</span>
                  ))}
                </div>
              )}
              
              <div className="mcp-actions">
                <div className="toggle-container">
                  <label className="toggle-switch">
                    <input 
                      type="checkbox" 
                      checked={getStatusClass(mcp) === 'running'}
                      onChange={() => handleStartStop(mcp.name, getStatusClass(mcp) === 'running' ? 'stop' : 'start')}
                      disabled={isLoading(mcp.name) || isCriticalMcp(mcp.name)}
                    />
                    <span className="toggle-slider"></span>
                  </label>
                  <span className="toggle-label">
                    {getStatusClass(mcp) === 'running' ? 'Enabled' : 'Disabled'}
                  </span>
                </div>
                
                <div className="action-buttons">
                  <button 
                    className="mcp-btn start"
                    onClick={() => handleStartStop(mcp.name, 'start')}
                    disabled={isLoading(mcp.name) || getStatusClass(mcp) === 'running'}
                  >
                    {isLoading(mcp.name) ? '...' : 'Start'}
                  </button>
                  <button 
                    className="mcp-btn stop"
                    onClick={() => handleStartStop(mcp.name, 'stop')}
                    disabled={isLoading(mcp.name) || getStatusClass(mcp) === 'stopped' || isCriticalMcp(mcp.name)}
                  >
                    {isLoading(mcp.name) ? '...' : 'Stop'}
                  </button>
                </div>
              </div>

              {getError(mcp.name) && (
                <div className="mcp-error">{getError(mcp.name)}</div>
              )}
              
              {mcp.config && (
                <div className="mcp-config">
                  <details>
                    <summary>Configuration</summary>
                    <pre>{JSON.stringify(mcp.config, null, 2)}</pre>
                  </details>
                </div>
              )}
            </div>
          ))
        )}
      </div>

      {discover && (
        <div className="discover-section">
          <h3>Discover Info</h3>
          <div className="discover-info">
            {discover.version && (
              <p><strong>Version:</strong> {discover.version}</p>
            )}
            {discover.endpoints && (
              <p><strong>Endpoints:</strong> {discover.endpoints.length}</p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default McpStatus