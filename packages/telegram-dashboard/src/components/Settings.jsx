import { useState, useEffect } from 'react'
import { api } from '../services/api'
import ModelSelector from './ModelSelector'

// Accordion Section Component
function AccordionSection({ title, icon, isOpen, onToggle, children, badge }) {
  return (
    <div className={`accordion-section ${isOpen ? 'open' : ''}`}>
      <button className="accordion-header" onClick={onToggle}>
        <div className="accordion-header-left">
          <span className="accordion-icon">{icon}</span>
          <span className="accordion-title">{title}</span>
          {badge && <span className="accordion-badge">{badge}</span>}
        </div>
        <span className={`accordion-arrow ${isOpen ? 'open' : ''}`}>▼</span>
      </button>
      <div className={`accordion-content ${isOpen ? 'open' : ''}`}>
        {children}
      </div>
    </div>
  )
}

function Settings({ 
  agents = [], 
  tools = [], 
  skills = [], 
  mcps = [], 
  models = [], 
  routingStats = null,
  onNavigate 
}) {
  const [settings, setSettings] = useState({
    // General
    theme: 'dark',
    apiBase: 'http://localhost:8000',
    refreshInterval: 30000,
    autoSave: true,
    // Appearance
    fontSize: 14,
    animationsEnabled: true,
    // Connection
    selectedModel: '',
    connectionTimeout: 30000,
    maxRetries: 3,
    // Pomodoro
    pomodoroWorkDuration: 25,
    pomodoroBreakDuration: 5,
    pomodoroAutoStart: false,
    // Advanced
    debugMode: false,
    logLevel: 'info',
    // Voice
    voiceEnabled: false,
    voiceWhisper: 'base',
    // Keyboard shortcuts (placeholder)
    shortcuts: {
      save: 'Ctrl+S',
      refresh: 'Ctrl+R',
      toggleTheme: 'Ctrl+T',
      openSettings: 'Ctrl+,'
    }
  })
  
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  
  // Track which sections are expanded (default: General and Registry open)
  const [expandedSections, setExpandedSections] = useState({
    general: true,
    appearance: false,
    connection: false,
    registry: true,
    pomodoro: false,
    advanced: false,
    voice: false,
    about: false
  })

  useEffect(() => {
    async function loadSettings() {
      try {
        const result = await api.getSettings()
        if (result.status === 'ok' && result.data) {
          setSettings(prev => ({ ...prev, ...result.data }))
        }
      } catch (err) {
        console.error('Error loading settings:', err)
      }
    }
    loadSettings()
  }, [])

  const handleSave = async () => {
    setSaving(true)
    setSaved(false)
    try {
      await api.saveSettings(settings)
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } catch (err) {
      console.error('Error saving settings:', err)
    } finally {
      setSaving(false)
    }
  }

  const handleChange = (key, value) => {
    setSettings(prev => ({ ...prev, [key]: value }))
    setSaved(false)
  }

  const toggleSection = (section) => {
    setExpandedSections(prev => ({ ...prev, [section]: !prev[section] }))
  }

  // Helper to count enabled items
  const countEnabled = (items) => items?.filter(item => item.enabled !== false)?.length || 0

  // Helper for routing stats display
  const routingTotal = routingStats?.total_requests || 0
  const routingSuccess = routingStats?.successful_routes || 0

  return (
    <div className="settings">
      <div className="settings-header">
        <h3>Settings</h3>
        {saved && <span className="save-indicator">Saved!</span>}
      </div>

      {/* General Section */}
      <AccordionSection
        title="General"
        icon="⚙️"
        isOpen={expandedSections.general}
        onToggle={() => toggleSection('general')}
      >
        <div className="setting-item">
          <label>Theme</label>
          <div className="toggle-group">
            <button 
              className={`toggle-btn ${settings.theme === 'light' ? 'active' : ''}`}
              onClick={() => handleChange('theme', 'light')}
            >
              Light
            </button>
            <button 
              className={`toggle-btn ${settings.theme === 'dark' ? 'active' : ''}`}
              onClick={() => handleChange('theme', 'dark')}
            >
              Dark
            </button>
          </div>
        </div>
        
        <div className="setting-item">
          <label>API Endpoint</label>
          <input 
            type="text" 
            value={settings.apiBase}
            onChange={(e) => handleChange('apiBase', e.target.value)}
            placeholder="http://localhost:8000"
          />
        </div>
        
        <div className="setting-item">
          <label>Refresh Interval</label>
          <select 
            value={settings.refreshInterval}
            onChange={(e) => handleChange('refreshInterval', parseInt(e.target.value))}
          >
            <option value={10000}>10 seconds</option>
            <option value={30000}>30 seconds</option>
            <option value={60000}>1 minute</option>
            <option value={300000}>5 minutes</option>
          </select>
        </div>

        <div className="setting-item">
          <label>Auto-save Settings</label>
          <input 
            type="checkbox"
            checked={settings.autoSave}
            onChange={(e) => handleChange('autoSave', e.target.checked)}
          />
        </div>
      </AccordionSection>

      {/* Appearance Section */}
      <AccordionSection
        title="Appearance"
        icon="🎨"
        isOpen={expandedSections.appearance}
        onToggle={() => toggleSection('appearance')}
      >
        <div className="setting-item">
          <label>Font Size</label>
          <div className="slider-group">
            <input 
              type="range"
              min="12"
              max="20"
              value={settings.fontSize}
              onChange={(e) => handleChange('fontSize', parseInt(e.target.value))}
            />
            <span className="slider-value">{settings.fontSize}px</span>
          </div>
        </div>

        <div className="setting-item">
          <label>Enable Animations</label>
          <input 
            type="checkbox"
            checked={settings.animationsEnabled}
            onChange={(e) => handleChange('animationsEnabled', e.target.checked)}
          />
        </div>

        <div className="setting-item">
          <label>Theme (already in General)</label>
          <span className="setting-hint">theme can be changed in General section</span>
        </div>
      </AccordionSection>

      {/* Connection Section */}
      <AccordionSection
        title="Connection"
        icon="🔗"
        isOpen={expandedSections.connection}
        onToggle={() => toggleSection('connection')}
      >
        <div className="setting-item">
          <label>Model Selection</label>
          <ModelSelector />
        </div>
        
        <div className="setting-item">
          <label>Connection Timeout</label>
          <select 
            value={settings.connectionTimeout}
            onChange={(e) => handleChange('connectionTimeout', parseInt(e.target.value))}
          >
            <option value={5000}>5 seconds</option>
            <option value={10000}>10 seconds</option>
            <option value={30000}>30 seconds</option>
            <option value={60000}>1 minute</option>
          </select>
        </div>

        <div className="setting-item">
          <label>Max Retries</label>
          <select 
            value={settings.maxRetries}
            onChange={(e) => handleChange('maxRetries', parseInt(e.target.value))}
          >
            <option value={1}>1 retry</option>
            <option value={2}>2 retries</option>
            <option value={3}>3 retries</option>
            <option value={5}>5 retries</option>
          </select>
        </div>
      </AccordionSection>

      {/* Registry Section */}
      <AccordionSection
        title="Registry"
        icon="📦"
        isOpen={expandedSections.registry}
        onToggle={() => toggleSection('registry')}
        badge={`${countEnabled(agents) + countEnabled(mcps)} active`}
      >
        <div className="registry-grid">
          {/* Agents */}
          <div className="registry-card">
            <div className="registry-icon">🤖</div>
            <div className="registry-info">
              <span className="registry-name">Agents</span>
              <span className="registry-stats">
                {countEnabled(agents)}/{agents?.length || 0} enabled
              </span>
            </div>
            <button 
              className="manage-btn"
              onClick={() => onNavigate?.('Agents')}
            >
              Manage
            </button>
          </div>

          {/* Tools */}
          <div className="registry-card">
            <div className="registry-icon">🔧</div>
            <div className="registry-info">
              <span className="registry-name">Tools</span>
              <span className="registry-stats">
                {tools?.length || 0} available
              </span>
            </div>
            <button 
              className="manage-btn"
              onClick={() => onNavigate?.('Tools')}
            >
              Manage
            </button>
          </div>

          {/* Skills */}
          <div className="registry-card">
            <div className="registry-icon">✨</div>
            <div className="registry-info">
              <span className="registry-name">Skills</span>
              <span className="registry-stats">
                {skills?.length || 0} available
              </span>
            </div>
            <button 
              className="manage-btn"
              onClick={() => onNavigate?.('Skills')}
            >
              Manage
            </button>
          </div>

          {/* MCPs */}
          <div className="registry-card">
            <div className="registry-icon">🔌</div>
            <div className="registry-info">
              <span className="registry-name">MCPs</span>
              <span className="registry-stats">
                {countEnabled(mcps)}/{mcps?.length || 0} active
              </span>
            </div>
            <button 
              className="manage-btn"
              onClick={() => onNavigate?.('MCP')}
            >
              Manage
            </button>
          </div>

          {/* Models */}
          <div className="registry-card">
            <div className="registry-icon">🧠</div>
            <div className="registry-info">
              <span className="registry-name">Models</span>
              <span className="registry-stats">
                {models?.length || 0} Ollama
              </span>
            </div>
            <button 
              className="manage-btn"
              onClick={() => onNavigate?.('Dashboard')}
            >
              Manage
            </button>
          </div>

          {/* Routing */}
          <div className="registry-card">
            <div className="registry-icon">🛤️</div>
            <div className="registry-info">
              <span className="registry-name">Routing</span>
              <span className="registry-stats">
                {routingSuccess}/{routingTotal} requests
              </span>
            </div>
            <button 
              className="manage-btn"
              onClick={() => onNavigate?.('Dashboard')}
            >
              View
            </button>
          </div>
        </div>
      </AccordionSection>

      {/* Pomodoro Section */}
      <AccordionSection
        title="Pomodoro"
        icon="🍅"
        isOpen={expandedSections.pomodoro}
        onToggle={() => toggleSection('pomodoro')}
      >
        <div className="setting-item">
          <label>Work Duration (minutes)</label>
          <select 
            value={settings.pomodoroWorkDuration}
            onChange={(e) => handleChange('pomodoroWorkDuration', parseInt(e.target.value))}
          >
            <option value={15}>15 minutes</option>
            <option value={25}>25 minutes</option>
            <option value={30}>30 minutes</option>
            <option value={45}>45 minutes</option>
            <option value={60}>60 minutes</option>
          </select>
        </div>

        <div className="setting-item">
          <label>Break Duration (minutes)</label>
          <select 
            value={settings.pomodoroBreakDuration}
            onChange={(e) => handleChange('pomodoroBreakDuration', parseInt(e.target.value))}
          >
            <option value={5}>5 minutes</option>
            <option value={10}>10 minutes</option>
            <option value={15}>15 minutes</option>
            <option value={20}>20 minutes</option>
          </select>
        </div>

        <div className="setting-item">
          <label>Auto-start Breaks</label>
          <input 
            type="checkbox"
            checked={settings.pomodoroAutoStart}
            onChange={(e) => handleChange('pomodoroAutoStart', e.target.checked)}
          />
        </div>
      </AccordionSection>

      {/* Advanced Section */}
      <AccordionSection
        title="Advanced"
        icon="🔧"
        isOpen={expandedSections.advanced}
        onToggle={() => toggleSection('advanced')}
      >
        <div className="setting-item">
          <label>Debug Mode</label>
          <input 
            type="checkbox"
            checked={settings.debugMode}
            onChange={(e) => handleChange('debugMode', e.target.checked)}
          />
        </div>

        <div className="setting-item">
          <label>Log Level</label>
          <select 
            value={settings.logLevel}
            onChange={(e) => handleChange('logLevel', e.target.value)}
          >
            <option value="error">Error</option>
            <option value="warn">Warning</option>
            <option value="info">Info</option>
            <option value="debug">Debug</option>
          </select>
        </div>

        <div className="setting-item">
          <label>Keyboard Shortcuts</label>
          <div className="shortcuts-list">
            <div className="shortcut-item">
              <span className="shortcut-action">Save Settings</span>
              <span className="shortcut-key">{settings.shortcuts?.save || 'Ctrl+S'}</span>
            </div>
            <div className="shortcut-item">
              <span className="shortcut-action">Refresh Data</span>
              <span className="shortcut-key">{settings.shortcuts?.refresh || 'Ctrl+R'}</span>
            </div>
            <div className="shortcut-item">
              <span className="shortcut-action">Toggle Theme</span>
              <span className="shortcut-key">{settings.shortcuts?.toggleTheme || 'Ctrl+T'}</span>
            </div>
            <div className="shortcut-item">
              <span className="shortcut-action">Open Settings</span>
              <span className="shortcut-key">{settings.shortcuts?.openSettings || 'Ctrl+,'}</span>
            </div>
          </div>
          <span className="setting-hint">Customization coming soon</span>
        </div>
      </AccordionSection>

      {/* Voice Section */}
      <AccordionSection
        title="Voice"
        icon="🎤"
        isOpen={expandedSections.voice}
        onToggle={() => toggleSection('voice')}
      >
        <div className="setting-item">
          <label>Enable Voice</label>
          <input 
            type="checkbox"
            checked={settings.voiceEnabled}
            onChange={(e) => handleChange('voiceEnabled', e.target.checked)}
          />
        </div>
        
        {settings.voiceEnabled && (
          <div className="setting-item">
            <label>Whisper Model</label>
            <select 
              value={settings.voiceWhisper}
              onChange={(e) => handleChange('voiceWhisper', e.target.value)}
            >
              <option value="tiny">tiny</option>
              <option value="base">base</option>
              <option value="small">small</option>
              <option value="medium">medium</option>
            </select>
          </div>
        )}
      </AccordionSection>

      {/* About Section */}
      <AccordionSection
        title="About"
        icon="ℹ️"
        isOpen={expandedSections.about}
        onToggle={() => toggleSection('about')}
      >
        <p className="about-text">N-Xyme MIND Dashboard</p>
        <p className="version">Version 1.0.0</p>
      </AccordionSection>

      <button 
        className="save-btn"
        onClick={handleSave}
        disabled={saving}
      >
        {saving ? 'Saving...' : 'Save Settings'}
      </button>
    </div>
  )
}

export default Settings