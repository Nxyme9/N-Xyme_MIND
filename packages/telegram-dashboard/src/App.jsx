import { useState, useEffect } from 'react'
import { api, getTelegramUser } from './services/api'
import { ChatProvider } from './context/ChatContext'
import AgentSelector from './components/AgentSelector'
import ToolExplorer from './components/ToolExplorer'
import SkillBrowser from './components/SkillBrowser'
import McpStatus from './components/McpStatus'
import StatusPanel from './components/StatusPanel'
import Sessions from './components/Sessions'
import TaskChecklist from './components/TaskChecklist'
import Settings from './components/Settings'
import Chat from './components/Chat'
import WindowManager from './components/WindowManager'
import Pomodoro from './components/Pomodoro'
import './App.css'

const TABS = ['Dashboard', 'Chat', 'Agents', 'Tools', 'Skills', 'MCP', 'Sessions', 'Tasks', 'Settings']

function App() {
  const [activeTab, setActiveTab] = useState('Dashboard')
  const [pomodoroOpen, setPomodoroOpen] = useState(false)
  const [user, setUser] = useState(null)
  const [data, setData] = useState({
    agents: [],
    tools: [],
    skills: [],
    mcps: [],
    discover: null,
    progress: null,
    routingStats: null,
    models: []
  })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // Get Telegram user on mount
  useEffect(() => {
    const tgUser = getTelegramUser()
    if (tgUser) {
      setUser(tgUser)
    }
  }, [])

  // Fetch all data on mount
  useEffect(() => {
    async function fetchData() {
      setLoading(true)
      setError(null)
      
      try {
        const [agents, tools, skills, mcps, discover, progress, routingStats, models] = 
          await Promise.allSettled([
            api.getAgents(),
            api.getTools(),
            api.getSkills(),
            api.getMcps(),
            api.getDiscover(),
            api.getLearningProgress(),
            api.getRoutingStats(),
            api.getLocalModels()
          ])
        
        // Transform skills data from backend format to flat array expected by SkillBrowser
        const rawSkills = skills.status === 'fulfilled' ? skills.value?.data || skills.value || [] : []
        let transformedSkills = []
        if (rawSkills && typeof rawSkills === 'object') {
          // Handle {learning_engine: [...], intelligence: {...}} format
          if (Array.isArray(rawSkills)) {
            transformedSkills = rawSkills
          } else {
            const learningSkills = Array.isArray(rawSkills.learning_engine) ? rawSkills.learning_engine : []
            // Transform intelligence from object to array format
            const intelligenceSkills = rawSkills.intelligence ? 
              Object.entries(rawSkills.intelligence).map(([key, val]) => ({
                id: key,
                name: val.name || key,
                category: val.category || 'general', 
                description: val.description || '',
                commands: []
              })) : [];
            // Merge and transform to {name, category, id, description, commands} format
            transformedSkills = [...learningSkills, ...intelligenceSkills].map(skill => ({
              id: skill.id || skill.name?.toLowerCase().replace(/\s+/g, '-'),
              name: skill.name,
              category: skill.category || 'general',
              description: skill.description || '',
              commands: skill.commands || []
            }))
          }
        }
        
        // Transform MCPs from object to array format
        const mcpsData = mcps.status === 'fulfilled' ? mcps.value?.data || {} : {};
        const transformedMcps = Object.entries(mcpsData).map(([name, config]) => ({
          name,
          ...config
        }));
        
        setData({
          agents: agents.status === 'fulfilled' ? agents.value?.data || agents.value || [] : [],
          tools: tools.status === 'fulfilled' ? tools.value?.data || tools.value || [] : [],
          skills: transformedSkills,
          mcps: transformedMcps,
          discover: discover.status === 'fulfilled' ? discover.value?.data || discover.value : null,
          progress: progress.status === 'fulfilled' ? progress.value?.data || progress.value : null,
          routingStats: routingStats.status === 'fulfilled' ? routingStats.value?.data || routingStats.value : null,
          models: models.status === 'fulfilled' ? models.value?.models || models.value || [] : []
        })
      } catch (err) {
        console.error('Failed to fetch data:', err)
        setError('Failed to load registry data')
      } finally {
        setLoading(false)
      }
    }
    
    fetchData()
  }, [])

  // Refresh MCP data
  const refreshMcpData = async () => {
    try {
      const mcpsData = await api.getMcps()
      const transformedMcps = Object.entries(mcpsData?.data || mcpsData || {}).map(([name, config]) => ({
        name,
        ...config
      }))
      setData(prev => ({ ...prev, mcps: transformedMcps }))
    } catch (err) {
      console.error('Failed to refresh MCP data:', err)
    }
  }

  const renderContent = () => {
    if (loading) {
      return (
        <div className="loading">
          <div className="spinner"></div>
          <p>Loading registry data...</p>
        </div>
      )
    }

    if (error) {
      return (
        <div className="error">
          <p>{error}</p>
          <button onClick={() => window.location.reload()}>Retry</button>
        </div>
      )
    }

    switch (activeTab) {
      case 'Dashboard':
        return (
          <div className="dashboard">
            <StatusPanel 
              progress={data.progress} 
              routingStats={data.routingStats}
            />
            <div className="stats-grid">
              <div 
                className="stat-card" 
                onClick={() => setActiveTab('Agents')}
                onKeyDown={(e) => e.key === 'Enter' && setActiveTab('Agents')}
                role="button"
                aria-label="View Agents"
                tabIndex={0}
              >
                <span className="stat-value">{data.agents.length}</span>
                <span className="stat-label">Agents</span>
              </div>
              <div 
                className="stat-card" 
                onClick={() => setActiveTab('Tools')}
                onKeyDown={(e) => e.key === 'Enter' && setActiveTab('Tools')}
                role="button"
                aria-label="View Tools"
                tabIndex={0}
              >
                <span className="stat-value">{data.tools.length}</span>
                <span className="stat-label">Tools</span>
              </div>
              <div 
                className="stat-card" 
                onClick={() => setActiveTab('Skills')}
                onKeyDown={(e) => e.key === 'Enter' && setActiveTab('Skills')}
                role="button"
                aria-label="View Skills"
                tabIndex={0}
              >
                <span className="stat-value">{data.skills.length}</span>
                <span className="stat-label">Skills</span>
              </div>
              <div 
                className="stat-card" 
                onClick={() => setActiveTab('MCP')}
                onKeyDown={(e) => e.key === 'Enter' && setActiveTab('MCP')}
                role="button"
                aria-label="View MCPs"
                tabIndex={0}
              >
                <span className="stat-value">{data.mcps.length}</span>
                <span className="stat-label">MCPs</span>
              </div>
            </div>
          </div>
        )
      
      case 'Chat':
        return <WindowManager />
      
      case 'Agents':
        return <AgentSelector agents={data.agents} />
      
      case 'Tools':
        return <ToolExplorer tools={data.tools} />
      
      case 'Skills':
        return <SkillBrowser skills={data.skills} />
      
      case 'MCP':
        return <McpStatus mcps={data.mcps} discover={data.discover} onRefresh={refreshMcpData} />
      
      case 'Sessions':
        return <Sessions />
      
      case 'Tasks':
        return <TaskChecklist />
      
      case 'Settings':
        return <Settings 
          agents={data.agents} 
          tools={data.tools} 
          skills={data.skills} 
          mcps={data.mcps}
          models={data.models}
          routingStats={data.routingStats}
          onNavigate={setActiveTab}
        />
      
      default:
        return null
    }
  }

  return (
    <ChatProvider>
      <div className="app">
        {/* Header */}
        <header className="header">
          <div className="header-content">
            <h1 className="app-title">N-Xyme MIND</h1>
            {user && (
              <div className="user-info">
                <img 
                  src={user.photo_url || 'https://telegram.org/img/t_logo.png'} 
                  alt={user.first_name}
                  className="user-avatar"
                />
                <span className="user-name">{user.first_name}</span>
              </div>
            )}
          </div>
        </header>

        {/* Tab Navigation */}
        <nav className="tabs">
          {TABS.map(tab => (
            <button
              key={tab}
              className={`tab ${activeTab === tab ? 'active' : ''}`}
              onClick={() => setActiveTab(tab)}
            >
              {tab}
            </button>
          ))}
        </nav>

        {/* Main Content */}
        <main className="content">
          {renderContent()}
        </main>

        {/* Floating Pomodoro Toggle Button */}
        <button 
          className={`pomodoro-float-btn ${pomodoroOpen ? 'active' : ''}`}
          onClick={() => setPomodoroOpen(!pomodoroOpen)}
          title="Pomodoro Timer"
        >
          <span className="pomodoro-icon">🍅</span>
        </button>

        {/* Pomodoro Slide-Out Panel */}
        <div className={`pomodoro-panel ${pomodoroOpen ? 'open' : ''}`}>
          <div className="pomodoro-panel-header">
            <span>Pomodoro Timer</span>
            <button 
              className="pomodoro-panel-close"
              onClick={() => setPomodoroOpen(false)}
            >
              ✕
            </button>
          </div>
          <div className="pomodoro-panel-content">
            <Pomodoro />
          </div>
        </div>
      </div>
    </ChatProvider>
  )
}

export default App
