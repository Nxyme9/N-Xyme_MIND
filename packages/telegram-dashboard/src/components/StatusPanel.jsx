function StatusPanel({ progress, routingStats }) {
  // Handle routing stats - progress param kept for future use
  const _progress = progress // reserved for future learning progress display
  const routing = routingStats?.data || routingStats || {}
  
  // Extract actual data from API response
  const agentPerformance = routing?.agent_performance || {}
  const qLearning = routing?.q_learning || {}
  
  // Get agents from agent_performance object
  const agents = Object.entries(agentPerformance).map(([name, data]) => ({
    agent: name,
    rate: data.success_rate || data.successRate || 0,
    total: data.total_tasks || data.totalTasks || 0,
    avg_latency: data.avg_latency_ms || data.avgLatencyMs || 0
  }))
  
  // Calculate aggregate stats
  const totalTasks = agents.reduce((sum, a) => sum + (a.total || 0), 0)
  const avgSuccessRate = agents.length > 0 
    ? agents.reduce((sum, a) => sum + (a.rate || 0), 0) / agents.length 
    : 0
  
  // Get Q-Learning stats if available
  const routingWeightCount = qLearning?.routing_weights ? Object.keys(qLearning.routing_weights).length : 0
  
  // If no data available at all
  const hasData = totalTasks > 0 || Object.keys(agentPerformance).length > 0 || Object.keys(qLearning).length > 0
  
  if (!hasData) {
    return (
      <div className="status-panel">
        <h2>System Status</h2>
        <p className="no-data">No routing data available</p>
      </div>
    )
  }

  return (
    <div className="status-panel">
      <h2>System Status</h2>
      
      <div className="status-grid">
        <div className="status-item">
          <span className="status-label">Total Tasks</span>
          <span className="status-value">{totalTasks}</span>
        </div>
        
        <div className="status-item">
          <span className="status-label">Avg Success Rate</span>
          <span className="status-value success">{(avgSuccessRate * 100).toFixed(1)}%</span>
        </div>
        
        <div className="status-item">
          <span className="status-label">Active Agents</span>
          <span className="status-value">{agents.length}</span>
        </div>
        
        <div className="status-item">
          <span className="status-label">Routing Weights</span>
          <span className="status-value">{routingWeightCount}</span>
        </div>
      </div>

      {agents.length > 0 && (
        <div className="agent-status">
          <h3>Agent Performance</h3>
          <div className="agent-progress">
            {agents.map((agent, index) => (
              <div key={agent.agent || index} className="agent-progress-item">
                <span className="agent-name">{agent.agent}</span>
                <div className="progress-bar">
                  <div 
                    className="progress-fill"
                    style={{ width: `${(agent.rate || 0) * 100}%` }}
                  ></div>
                </div>
                <span className="agent-rate">{((agent.rate || 0) * 100).toFixed(0)}%</span>
                <span className="agent-tasks">({agent.total} tasks)</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {Object.keys(qLearning).length > 0 && (
        <div className="routing-stats">
          <h3>Routing Intelligence</h3>
          <div className="stats-row">
            {qLearning.total_predictions !== undefined && (
              <div className="stat">
                <span className="stat-label">Total Predictions</span>
                <span className="stat-value">{qLearning.total_predictions}</span>
              </div>
            )}
            {qLearning.accuracy !== undefined && (
              <div className="stat">
                <span className="stat-label">Accuracy</span>
                <span className="stat-value">{((qLearning.accuracy || 0) * 100).toFixed(1)}%</span>
              </div>
            )}
            {qLearning.avg_confidence !== undefined && (
              <div className="stat">
                <span className="stat-label">Avg Confidence</span>
                <span className="stat-value">{(qLearning.avg_confidence * 100).toFixed(1)}%</span>
              </div>
            )}
            {qLearning.exploitation_rate !== undefined && (
              <div className="stat">
                <span className="stat-label">Exploitation</span>
                <span className="stat-value">{(qLearning.exploitation_rate * 100).toFixed(0)}%</span>
              </div>
            )}
            {qLearning.exploration_rate !== undefined && (
              <div className="stat">
                <span className="stat-label">Exploration</span>
                <span className="stat-value">{(qLearning.exploration_rate * 100).toFixed(0)}%</span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default StatusPanel