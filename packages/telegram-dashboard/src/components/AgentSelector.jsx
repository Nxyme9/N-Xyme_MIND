import { useState } from 'react'

function AgentSelector({ agents }) {
  const [selected, setSelected] = useState(null)
  const [filter, setFilter] = useState('')

  // Defensive: ensure agents is an array
  const agentsArray = Array.isArray(agents) ? agents : []
  const filteredAgents = agentsArray.filter(agent => 
    agent.name?.toLowerCase().includes(filter.toLowerCase()) ||
    agent.role?.toLowerCase().includes(filter.toLowerCase())
  )

  return (
    <div className="agent-selector">
      <div className="search-bar">
        <input
          type="text"
          placeholder="Search agents..."
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="search-input"
        />
      </div>

      <div className="agent-grid">
        {filteredAgents.length === 0 ? (
          <p className="empty">No agents found</p>
        ) : (
          filteredAgents.map((agent, index) => (
            <div
              key={agent.id || index}
              className={`agent-card ${selected === index ? 'selected' : ''}`}
              onClick={() => setSelected(selected === index ? null : index)}
            >
              <div className="agent-icon">
                {agent.name?.charAt(0).toUpperCase() || 'A'}
              </div>
              <div className="agent-info">
                <h3>{agent.name || 'Unknown Agent'}</h3>
                <p className="agent-role">{agent.role || 'General'}</p>
                {agent.model && (
                  <p className="agent-model">{agent.model}</p>
                )}
              </div>
              {selected === index && agent.description && (
                <p className="agent-desc">{agent.description}</p>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  )
}

export default AgentSelector