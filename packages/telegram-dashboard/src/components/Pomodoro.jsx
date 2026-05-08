import { useState, useEffect, useRef, useCallback } from 'react'

const WORK_TIME = 25 * 60  // 25 minutes in seconds
const BREAK_TIME = 5 * 60  // 5 minutes in seconds

function Pomodoro() {
  const [timeLeft, setTimeLeft] = useState(WORK_TIME)
  const [isRunning, setIsRunning] = useState(false)
  const [isBreak, setIsBreak] = useState(false)
  const [sessions, setSessions] = useState(0)
  const intervalRef = useRef(null)

  // Format time as MM:SS
  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }

  // Calculate progress percentage
  const totalTime = isBreak ? BREAK_TIME : WORK_TIME
  const progress = ((totalTime - timeLeft) / totalTime) * 100

  // Timer logic
  useEffect(() => {
    if (!isRunning || timeLeft > 0) {
      if (isRunning && timeLeft > 0) {
        intervalRef.current = setInterval(() => {
          setTimeLeft(prev => prev - 1)
        }, 1000)
      }
      return () => clearInterval(intervalRef.current)
    }
    
    // Timer completed - use callback pattern to avoid setState in effect
    const handleTimerComplete = () => {
      setIsRunning(false)
      
      if (!isBreak) {
        setSessions(prev => prev + 1)
        setIsBreak(true)
        setTimeLeft(BREAK_TIME)
      } else {
        setIsBreak(false)
        setTimeLeft(WORK_TIME)
      }
    }
    
    handleTimerComplete()
  }, [isRunning, timeLeft, isBreak])

  const toggleTimer = () => setIsRunning(!isRunning)
  
  const resetTimer = useCallback(() => {
    setIsRunning(false)
    setTimeLeft(isBreak ? BREAK_TIME : WORK_TIME)
  }, [isBreak])
  
  const skipPhase = useCallback(() => {
    setIsRunning(false)
    if (isBreak) {
      setIsBreak(false)
      setTimeLeft(WORK_TIME)
    } else {
      setSessions(prev => prev + 1)
      setIsBreak(true)
      setTimeLeft(BREAK_TIME)
    }
  }, [isBreak])

  const resetAll = () => {
    setIsRunning(false)
    setIsBreak(false)
    setTimeLeft(WORK_TIME)
    setSessions(0)
  }

  return (
    <div className="pomodoro-container">
      <h2>Pomodoro Timer</h2>
      
      <div className="pomodoro-display">
        <div className="pomodoro-phase">
          {isBreak ? '☕ Break Time' : '🎯 Work Time'}
        </div>
        
        <div className="pomodoro-time">
          {formatTime(timeLeft)}
        </div>
        
        <div className="pomodoro-progress">
          <div 
            className="progress-bar"
            style={{ width: `${progress}%` }}
          ></div>
        </div>
        
        <div className="pomodoro-sessions">
          Sessions completed: {sessions}
        </div>
      </div>
      
      <div className="pomodoro-controls">
        <button 
          onClick={toggleTimer} 
          className={`pomodoro-btn ${isRunning ? 'pause' : 'start'}`}
        >
          {isRunning ? '⏸ Pause' : '▶ Start'}
        </button>
        
        <button onClick={resetTimer} className="pomodoro-btn reset">
          ↺ Reset
        </button>
        
        <button onClick={skipPhase} className="pomodoro-btn skip">
          ⏭ Skip
        </button>
      </div>
      
      <div className="pomodoro-info">
        <p>25 min work / 5 min break</p>
        <button onClick={resetAll} className="reset-all-btn">
          Reset All
        </button>
      </div>
    </div>
  )
}

export default Pomodoro
