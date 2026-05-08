import { useState } from 'react'

function TaskChecklist() {
  const [tasks, setTasks] = useState([
    { id: 1, title: 'Fix JSON serialization error', status: 'completed', priority: 'high' },
    { id: 2, title: 'Add model endpoints to server.py', status: 'completed', priority: 'high' },
    { id: 3, title: 'Update api.js with new endpoints', status: 'completed', priority: 'high' },
    { id: 4, title: 'Create ModelSelector component', status: 'in_progress', priority: 'high' },
    { id: 5, title: 'Create Sessions component', status: 'completed', priority: 'high' },
    { id: 6, title: 'Create TaskChecklist component', status: 'in_progress', priority: 'high' },
    { id: 7, title: 'Update Settings with real settings', status: 'pending', priority: 'medium' },
    { id: 8, title: 'Update App.jsx with new tabs', status: 'pending', priority: 'high' },
    { id: 9, title: 'Build and test dashboard', status: 'pending', priority: 'high' },
  ])
  const [newTaskTitle, setNewTaskTitle] = useState('')

  const getStatusIcon = (status) => {
    switch (status) {
      case 'completed': return '✓'
      case 'in_progress': return '◐'
      case 'pending': return '○'
      default: return '○'
    }
  }

  const getStatusClass = (status) => {
    switch (status) {
      case 'completed': return 'status-completed'
      case 'in_progress': return 'status-progress'
      case 'pending': return 'status-pending'
      default: return ''
    }
  }

  const toggleTaskStatus = (taskId) => {
    setTasks(tasks.map(task => {
      if (task.id === taskId) {
        const nextStatus = task.status === 'pending' ? 'in_progress' 
          : task.status === 'in_progress' ? 'completed' 
          : 'pending'
        return { ...task, status: nextStatus }
      }
      return task
    }))
  }

  const addTask = () => {
    if (!newTaskTitle.trim()) return
    const newTask = {
      id: Date.now(),
      title: newTaskTitle.trim(),
      status: 'pending',
      priority: 'medium'
    }
    setTasks([...tasks, newTask])
    setNewTaskTitle('')
  }

  const deleteTask = (taskId) => {
    setTasks(tasks.filter(t => t.id !== taskId))
  }

  const completedCount = tasks.filter(t => t.status === 'completed').length
  const progress = Math.round((completedCount / tasks.length) * 100)

  return (
    <div className="task-checklist">
      <div className="task-header">
        <h3>Task Checklist</h3>
        <div className="task-progress">
          <div className="progress-bar">
            <div className="progress-fill" style={{ width: `${progress}%` }}></div>
          </div>
          <span className="progress-text">{completedCount}/{tasks.length} ({progress}%)</span>
        </div>
      </div>

      <div className="task-add">
        <input
          type="text"
          placeholder="Add a new task..."
          value={newTaskTitle}
          onChange={(e) => setNewTaskTitle(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && addTask()}
        />
        <button onClick={addTask} disabled={!newTaskTitle.trim()}>+</button>
      </div>

      <div className="task-list">
        {tasks.map(task => (
          <div key={task.id} className={`task-item ${getStatusClass(task.status)}`}>
            <button 
              className="task-checkbox"
              onClick={() => toggleTaskStatus(task.id)}
            >
              {getStatusIcon(task.status)}
            </button>
            <span className="task-title">{task.title}</span>
            <span className={`task-priority priority-${task.priority}`}>
              {task.priority}
            </span>
            <button 
              className="task-delete"
              onClick={() => deleteTask(task.id)}
            >
              ×
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}

export default TaskChecklist