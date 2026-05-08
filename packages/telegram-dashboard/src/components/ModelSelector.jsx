import { useState, useEffect } from 'react'
import { api } from '../services/api'

function ModelSelector({ onModelChange }) {
  const [localModels, setLocalModels] = useState([])
  const [ollamaModels, setOllamaModels] = useState([])
  const [selectedModel, setSelectedModel] = useState(null)
  const [modelStatus, setModelStatus] = useState(null)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('local')

  useEffect(() => {
    async function fetchModels() {
      setLoading(true)
      try {
        const [local, ollama, status] = await Promise.all([
          api.getLocalModels(),
          api.getOllamaModels(),
          api.getModelStatus()
        ])
        
        if (local.status === 'ok') {
          setLocalModels(local.models || [])
        }
        if (ollama.status === 'ok') {
          setOllamaModels(ollama.models || [])
        }
        if (status.status === 'ok') {
          setModelStatus(status)
        }
      } catch (err) {
        console.error('Error fetching models:', err)
      } finally {
        setLoading(false)
      }
    }
    fetchModels()
  }, [])

  const handleSelectModel = async (model, source) => {
    setSelectedModel({ ...model, source })
    if (onModelChange) {
      onModelChange(model, source)
    }
  }

  const handleLoadModel = async (modelName) => {
    // Validate modelName is non-empty string
    if (!modelName || typeof modelName !== 'string' || modelName.trim() === '') {
      console.warn('Invalid modelName: must be non-empty string')
      return
    }
    try {
      const result = await api.loadModel(modelName, 'ollama')
      if (result.status === 'ok') {
        setModelStatus({ ...modelStatus, loaded: true, current: modelName })
      }
    } catch (err) {
      console.error('Error loading model:', err)
    }
  }

  const renderModelList = (models, source) => {
    if (models.length === 0) {
      return (
        <div className="no-models">
          <p>No {source} models available</p>
        </div>
      )
    }

    return models.map((model, idx) => (
      <div
        key={idx}
        className={`model-card ${selectedModel?.name === model.name ? 'selected' : ''}`}
        onClick={() => handleSelectModel(model, source)}
      >
        <div className="model-info">
          <span className="model-name">{model.name || model}</span>
          {model.size_mb && (
            <span className="model-size">{model.size_mb} MB</span>
          )}
          {model.size && (
            <span className="model-size">{Math.round(model.size / 1024 / 1024)} MB</span>
          )}
        </div>
        <div className="model-actions">
          {source === 'ollama' && (
            <button 
              className="load-btn"
              onClick={(e) => {
                e.stopPropagation()
                handleLoadModel(model.name)
              }}
            >
              Load
            </button>
          )}
        </div>
      </div>
    ))
  }

  if (loading) {
    return (
      <div className="model-selector loading">
        <div className="spinner"></div>
        <p>Loading models...</p>
      </div>
    )
  }

  return (
    <div className="model-selector">
      <div className="model-status">
        <span className={`status-badge ${modelStatus?.loaded ? 'loaded' : 'none'}`}>
          {modelStatus?.loaded ? `Loaded: ${modelStatus.current || 'Ready'}` : 'No model loaded'}
        </span>
      </div>

      <div className="model-tabs">
        <button 
          className={`tab ${activeTab === 'local' ? 'active' : ''}`}
          onClick={() => setActiveTab('local')}
        >
          Local GGUF ({localModels.length})
        </button>
        <button 
          className={`tab ${activeTab === 'ollama' ? 'active' : ''}`}
          onClick={() => setActiveTab('ollama')}
        >
          Ollama ({ollamaModels.length})
        </button>
      </div>

      <div className="model-list">
        {activeTab === 'local' ? renderModelList(localModels, 'local') : renderModelList(ollamaModels, 'ollama')}
      </div>

      {selectedModel && (
        <div className="selected-model">
          <h4>Selected Model</h4>
          <p>{selectedModel.name}</p>
          <span className="model-source">{selectedModel.source}</span>
        </div>
      )}
    </div>
  )
}

export default ModelSelector