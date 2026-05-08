import { useState } from 'react'
import api from '../services/api'

function ToolExplorer({ tools }) {
  const [selected, setSelected] = useState(null)
  const [filter, setFilter] = useState('')
  const [expandedTool, setExpandedTool] = useState(null)
  const [params, setParams] = useState({})
  const [executing, setExecuting] = useState(null)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  // Defensive: ensure tools is an array
  const toolsArray = Array.isArray(tools) ? tools : []
  const filteredTools = toolsArray.filter(tool => 
    tool.name?.toLowerCase().includes(filter.toLowerCase()) ||
    tool.category?.toLowerCase().includes(filter.toLowerCase())
  )

  // Get schema parameters from tool
  const getParameters = (tool) => {
    if (tool.parameters && Array.isArray(tool.parameters)) {
      return tool.parameters
    }
    if (tool.schema?.parameters?.properties) {
      return Object.entries(tool.schema.parameters.properties).map(([key, value]) => ({
        name: key,
        ...value,
        required: tool.schema.parameters.required?.includes(key)
      }))
    }
    return []
  }

  const handleExpand = (index) => {
    const newExpanded = expandedTool === index ? null : index
    setExpandedTool(newExpanded)
    setParams({})
    setResult(null)
    setError(null)
  }

  const handleParamChange = (paramName, value) => {
    setParams(prev => ({ ...prev, [paramName]: value }))
  }

  const handleExecute = async (tool) => {
    if (!tool.name) return
    
    // Check for dangerous tools
    const dangerousTools = ['delete', 'remove', 'drop', 'destroy', 'shutdown']
    const isDangerous = dangerousTools.some(d => tool.name.toLowerCase().includes(d))
    
    if (isDangerous && !window.confirm(`⚠️ This tool "${tool.name}" may be dangerous. Are you sure you want to execute it?`)) {
      return
    }

    setExecuting(tool.name)
    setResult(null)
    setError(null)

    try {
      const res = await api.executeTool(tool.name, params)
      setResult(res)
    } catch (err) {
      setError(err.message || 'Tool execution failed')
    } finally {
      setExecuting(null)
    }
  }

  return (
    <div className="tool-explorer">
      <div className="search-bar">
        <input
          type="text"
          placeholder="Search tools..."
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="search-input"
        />
      </div>

      <div className="tool-list">
        {filteredTools.length === 0 ? (
          <p className="empty">No tools found</p>
        ) : (
          filteredTools.map((tool, index) => {
            const parameters = getParameters(tool)
            const isExpanded = expandedTool === index
            const isExecuting = executing === tool.name

            return (
              <div key={tool.id || index} className="tool-item-wrapper">
                <div
                  className={`tool-item ${selected === index ? 'selected' : ''}`}
                  onClick={() => {
                    setSelected(selected === index ? null : index)
                    handleExpand(index)
                  }}
                >
                  <div className="tool-header">
                    <span className="tool-name">{tool.name || 'Unknown Tool'}</span>
                    <span className="tool-category">{tool.category || 'General'}</span>
                    {parameters.length > 0 && (
                      <span className="param-count">{parameters.length} params</span>
                    )}
                  </div>
                  {tool.description && (
                    <p className="tool-desc">{tool.description}</p>
                  )}
                  {selected === index && tool.capabilities && (
                    <div className="tool-caps">
                      {tool.capabilities.map((cap, i) => (
                        <span key={i} className="cap-tag">{cap}</span>
                      ))}
                    </div>
                  )}
                </div>

                {isExpanded && (
                  <div className="tool-execution-panel">
                    {parameters.length > 0 ? (
                      <div className="params-section">
                        <h4>Parameters</h4>
                        {parameters.map((param) => (
                          <div key={param.name} className="param-input">
                            <label>
                              {param.name}
                              {param.required && <span className="required">*</span>}
                              {param.description && <span className="param-desc"> - {param.description}</span>}
                            </label>
                            {param.enum ? (
                              <select
                                value={params[param.name] || ''}
                                onChange={(e) => handleParamChange(param.name, e.target.value)}
                                disabled={isExecuting}
                              >
                                <option value="">Select...</option>
                                {param.enum.map((opt) => (
                                  <option key={opt} value={opt}>{opt}</option>
                                ))}
                              </select>
                            ) : param.type === 'boolean' ? (
                              <input
                                type="checkbox"
                                checked={params[param.name] || false}
                                onChange={(e) => handleParamChange(param.name, e.target.checked)}
                                disabled={isExecuting}
                              />
                            ) : (
                              <input
                                type={param.type === 'integer' || param.type === 'number' ? 'number' : 'text'}
                                value={params[param.name] || ''}
                                onChange={(e) => handleParamChange(param.name, e.target.value)}
                                placeholder={param.description || `Enter ${param.name}`}
                                disabled={isExecuting}
                              />
                            )}
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="no-params">No parameters required</p>
                    )}

                    <button
                      className="run-btn"
                      onClick={(e) => {
                        e.stopPropagation()
                        handleExecute(tool)
                      }}
                      disabled={isExecuting}
                    >
                      {isExecuting ? (
                        <>
                          <span className="spinner"></span>
                          Executing...
                        </>
                      ) : (
                        '▶ Run'
                      )}
                    </button>

                    {result && (
                      <div className="result-section">
                        <div className="result-header">
                          <span>✓ Result</span>
                        </div>
                        <pre className="result-content">
                          {typeof result === 'object' ? JSON.stringify(result, null, 2) : result}
                        </pre>
                      </div>
                    )}

                    {error && (
                      <div className="error-section">
                        <div className="error-header">
                          <span>✕ Error</span>
                        </div>
                        <pre className="error-content">{error}</pre>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}

export default ToolExplorer