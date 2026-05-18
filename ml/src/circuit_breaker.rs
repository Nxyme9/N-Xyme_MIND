use std::collections::HashMap;
use std::time::{Duration, Instant};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CircuitState {
    Closed,
    Open,
    HalfOpen,
}

#[derive(Debug, Clone)]
pub struct CircuitBreaker {
    name: String,
    state: CircuitState,
    failure_count: u32,
    success_count: u32,
    failure_threshold: u32,
    success_threshold: u32,
    last_failure_time: Option<Instant>,
    recovery_timeout: Duration,
    consecutive_failures: u32,
}

impl CircuitBreaker {
    pub fn new(name: &str, failure_threshold: u32, success_threshold: u32, recovery_timeout: Duration) -> Self {
        Self {
            name: name.to_string(),
            state: CircuitState::Closed,
            failure_count: 0,
            success_count: 0,
            failure_threshold,
            success_threshold,
            last_failure_time: None,
            recovery_timeout,
            consecutive_failures: 0,
        }
    }

    pub fn name(&self) -> &str {
        &self.name
    }

    pub fn state(&self) -> CircuitState {
        self.state
    }

    pub fn can_execute(&self) -> bool {
        match self.state {
            CircuitState::Closed => true,
            CircuitState::HalfOpen => true,
            CircuitState::Open => {
                if let Some(last_fail) = self.last_failure_time {
                    last_fail.elapsed() >= self.recovery_timeout
                } else {
                    true
                }
            }
        }
    }

    pub fn record_success(&mut self) {
        self.success_count += 1;
        self.consecutive_failures = 0;

        match self.state {
            CircuitState::HalfOpen => {
                if self.success_count >= self.success_threshold {
                    self.state = CircuitState::Closed;
                    self.failure_count = 0;
                    self.success_count = 0;
                }
            }
            CircuitState::Open => {
                self.state = CircuitState::HalfOpen;
                self.success_count = 1;
            }
            CircuitState::Closed => {
                // Reset failure count on sustained success
                if self.success_count % 10 == 0 && self.failure_count > 0 {
                    self.failure_count = self.failure_count.saturating_sub(1);
                }
            }
        }
    }

    pub fn record_failure(&mut self) {
        self.failure_count += 1;
        self.consecutive_failures += 1;
        self.last_failure_time = Some(Instant::now());
        self.success_count = 0;

        match self.state {
            CircuitState::Closed => {
                if self.failure_count >= self.failure_threshold {
                    self.state = CircuitState::Open;
                    log::warn!(
                        "Circuit breaker '{}' opened after {} failures",
                        self.name,
                        self.failure_count
                    );
                }
            }
            CircuitState::HalfOpen => {
                self.state = CircuitState::Open;
                log::warn!(
                    "Circuit breaker '{}' re-opened from half-open after failure",
                    self.name
                );
            }
            CircuitState::Open => {
                // Already open, update timeout
                log::debug!(
                    "Circuit breaker '{}' still open, additional failure recorded",
                    self.name
                );
            }
        }
    }

    pub fn failure_rate(&self, window: Duration) -> f32 {
        let total = self.failure_count + self.success_count;
        if total == 0 {
            return 0.0;
        }
        self.failure_count as f32 / total as f32
    }

    pub fn consecutive_failures(&self) -> u32 {
        self.consecutive_failures
    }
}

pub struct CircuitBreakerRegistry {
    breakers: HashMap<String, CircuitBreaker>,
}

impl CircuitBreakerRegistry {
    pub fn new() -> Self {
        Self {
            breakers: HashMap::new(),
        }
    }

    pub fn register(&mut self, breaker: CircuitBreaker) {
        let name = breaker.name().to_string();
        self.breakers.insert(name, breaker);
    }

    pub fn get(&self, name: &str) -> Option<&CircuitBreaker> {
        self.breakers.get(name)
    }

    pub fn get_mut(&mut self, name: &str) -> Option<&mut CircuitBreaker> {
        self.breakers.get_mut(name)
    }

    pub fn can_execute(&self, name: &str) -> bool {
        self.breakers
            .get(name)
            .map(|b| b.can_execute())
            .unwrap_or(true)
    }

    pub fn record_success(&mut self, name: &str) {
        if let Some(breaker) = self.breakers.get_mut(name) {
            breaker.record_success();
        }
    }

    pub fn record_failure(&mut self, name: &str) {
        if let Some(breaker) = self.breakers.get_mut(name) {
            breaker.record_failure();
        }
    }

    pub fn all_open(&self) -> Vec<&CircuitBreaker> {
        self.breakers
            .values()
            .filter(|b| matches!(b.state(), CircuitState::Open))
            .collect()
    }

    pub fn count_by_state(&self, state: CircuitState) -> usize {
        self.breakers.values().filter(|b| b.state() == state).count()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_initial_state() {
        let breaker = CircuitBreaker::new("test", 3, 2, Duration::from_secs(60));
        assert_eq!(breaker.state(), CircuitState::Closed);
        assert!(breaker.can_execute());
    }

    #[test]
    fn test_open_on_failures() {
        let mut breaker = CircuitBreaker::new("test", 3, 2, Duration::from_secs(60));
        breaker.record_failure();
        breaker.record_failure();
        breaker.record_failure();
        assert_eq!(breaker.state(), CircuitState::Open);
        assert!(!breaker.can_execute());
    }

    #[test]
    fn test_half_open_recovery() {
        let mut breaker = CircuitBreaker::new("test", 3, 2, Duration::from_millis(1));
        breaker.record_failure();
        breaker.record_failure();
        breaker.record_failure();
        assert_eq!(breaker.state(), CircuitState::Open);
        std::thread::sleep(Duration::from_millis(2));
        assert!(breaker.can_execute());
        breaker.record_success();
        assert_eq!(breaker.state(), CircuitState::HalfOpen);
        breaker.record_success();
        assert_eq!(breaker.state(), CircuitState::Closed);
    }

    #[test]
    fn test_registry() {
        let mut registry = CircuitBreakerRegistry::new();
        registry.register(CircuitBreaker::new("tool_a", 3, 2, Duration::from_secs(60)));
        registry.register(CircuitBreaker::new("tool_b", 5, 3, Duration::from_secs(30)));
        assert!(registry.can_execute("tool_a"));
        assert!(registry.can_execute("tool_b"));
        assert!(registry.can_execute("nonexistent"));
    }
}
