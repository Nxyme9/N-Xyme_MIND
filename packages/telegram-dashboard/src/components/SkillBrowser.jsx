import { useState } from 'react'
import { api } from '../services/api'

function SkillBrowser({ skills }) {
  const [selected, setSelected] = useState(null)
  const [filter, setFilter] = useState('')
  const [executing, setExecuting] = useState(null)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  // Defensive: ensure skills is an array
  const skillsArray = Array.isArray(skills) ? skills : []
  const filteredSkills = skillsArray.filter(skill => 
    skill.name?.toLowerCase().includes(filter.toLowerCase()) ||
    skill.category?.toLowerCase().includes(filter.toLowerCase())
  )

  const handleExecute = async (skill, e) => {
    e.stopPropagation()
    
    // Skip dangerous skills without confirmation
    const dangerousPatterns = ['delete', 'remove', 'drop', 'destroy', 'shutdown', 'kill']
    const isDangerous = dangerousPatterns.some(p => 
      skill.name?.toLowerCase().includes(p) || 
      skill.description?.toLowerCase().includes(p)
    )
    
    if (isDangerous) {
      const confirmed = window.confirm(
        `⚠️ This skill "${skill.name}" may be dangerous. Execute anyway?`
      )
      if (!confirmed) return
    }

    setExecuting(skill.id || skill.name)
    setResult(null)
    setError(null)

    try {
      const executionResult = await api.executeSkill(skill.id || skill.name, {})
      setResult(executionResult)
    } catch (err) {
      setError(err.message || 'Execution failed')
    } finally {
      setExecuting(null)
    }
  }

  return (
    <div className="skill-browser">
      <div className="search-bar">
        <input
          type="text"
          placeholder="Search skills..."
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="search-input"
        />
      </div>

      <div className="skill-grid">
        {filteredSkills.length === 0 ? (
          <p className="empty">No skills found</p>
        ) : (
          filteredSkills.map((skill, index) => (
            <div
              key={skill.id || index}
              className={`skill-card ${selected === index ? 'selected' : ''}`}
              onClick={() => setSelected(selected === index ? null : index)}
            >
              <div className="skill-header">
                <div className="skill-icon">⚡</div>
                <div className="skill-info">
                  <h3>{skill.name || 'Unknown Skill'}</h3>
                  <p className="skill-category">{skill.category || 'General'}</p>
                </div>
                <button
                  className={`execute-btn ${executing === (skill.id || skill.name) ? 'loading' : ''}`}
                  onClick={(e) => handleExecute(skill, e)}
                  disabled={executing === (skill.id || skill.name)}
                >
                  {executing === (skill.id || skill.name) ? (
                    <span className="spinner">⟳</span>
                  ) : (
                    '▶ Run'
                  )}
                </button>
              </div>
              
              {skill.description && (
                <p className="skill-desc">{skill.description}</p>
              )}
              
              {skill.commands && skill.commands.length > 0 && (
                <div className="skill-commands">
                  <span className="commands-label">Commands:</span>
                  {skill.commands.map((cmd, i) => (
                    <code key={i} className="cmd">{cmd}</code>
                  ))}
                </div>
              )}

              {skill.parameters && skill.parameters.length > 0 && (
                <div className="skill-params">
                  <span className="params-label">Parameters:</span>
                  {skill.parameters.map((param, i) => (
                    <span key={i} className="param-badge" title={param.description}>
                      {param.name}
                      {param.required && <span className="required">*</span>}
                    </span>
                  ))}
                </div>
              )}

              {/* Execution Result */}
              {(result || error) && executing === null && selected === index && (
                <div className={`execution-result ${error ? 'error' : 'success'}`}>
                  <div className="result-header" onClick={() => { setResult(null); setError(null) }}>
                    {error ? `❌ Error` : '✅ Result'}
                    <span className="close-result">×</span>
                  </div>
                  <pre className="result-content">
                    {error || (typeof result === 'object' ? JSON.stringify(result, null, 2) : result)}
                  </pre>
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  )
}

export default SkillBrowser