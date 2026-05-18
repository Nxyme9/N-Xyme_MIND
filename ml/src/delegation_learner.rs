use std::collections::HashMap;

#[derive(Debug, Clone)]
pub struct AgentPerformance {
    pub agent: String,
    pub success_rate: f32,
    pub quality_score: f32,
    pub speed_score: f32,
    pub composite_score: f32,
    pub streak: i32,
    pub total_tasks: u32,
}

#[derive(Debug, Clone)]
pub struct TaskPerformance {
    pub agent: String,
    pub task_type: String,
    pub success: bool,
    pub quality: f32,
    pub duration_ms: u64,
    pub timestamp: std::time::Instant,
}

pub struct DelegationLearner {
    performances: HashMap<String, AgentPerformance>,
    task_history: Vec<TaskPerformance>,
}

impl DelegationLearner {
    pub fn new() -> Self {
        Self {
            performances: HashMap::new(),
            task_history: Vec::new(),
        }
    }

    pub fn record_outcome(&mut self, agent: &str, task_type: &str, success: bool, quality: f32, duration_ms: u64) {
        let entry = self.performances.entry(agent.to_string()).or_insert(AgentPerformance {
            agent: agent.to_string(),
            success_rate: 0.0,
            quality_score: 0.0,
            speed_score: 0.0,
            composite_score: 0.0,
            streak: 0,
            total_tasks: 0,
        });

        entry.total_tasks += 1;
        if success {
            entry.streak = entry.streak.saturating_add(1);
        } else {
            entry.streak = 0;
        }

        // Update success rate (exponential moving average)
        let alpha = 0.3;
        entry.success_rate = entry.success_rate * (1.0 - alpha) + if success { 1.0 } else { 0.0 } * alpha;
        entry.quality_score = entry.quality_score * (1.0 - alpha) + quality * alpha;

        // Speed score: faster is better (capped at 1.0)
        let speed = (1000.0 / duration_ms as f32).min(1.0);
        entry.speed_score = entry.speed_score * (1.0 - alpha) + speed * alpha;

        // Composite: 50% success rate, 30% quality, 20% speed
        entry.composite_score = entry.success_rate * 0.5 + entry.quality_score * 0.3 + entry.speed_score * 0.2;

        self.task_history.push(TaskPerformance {
            agent: agent.to_string(),
            task_type: task_type.to_string(),
            success,
            quality,
            duration_ms,
            timestamp: std::time::Instant::now(),
        });
    }

    pub fn select_best_agent(&self, task_type: &str) -> Option<String> {
        self.performances
            .iter()
            .filter(|(_, perf)| perf.total_tasks > 0)
            .max_by(|(_, a), (_, b)| a.composite_score.partial_cmp(&b.composite_score).unwrap())
            .map(|(agent, _)| agent.clone())
    }

    pub fn get_performance(&self, agent: &str) -> Option<&AgentPerformance> {
        self.performances.get(agent)
    }

    pub fn get_all_performances(&self) -> Vec<&AgentPerformance> {
        let mut results: Vec<&AgentPerformance> = self.performances.values().collect();
        results.sort_by(|a, b| b.composite_score.partial_cmp(&a.composite_score).unwrap());
        results
    }

    pub fn detect_decay(&self, agent: &str, threshold: f32) -> bool {
        self.performances
            .get(agent)
            .map(|perf| {
                if perf.total_tasks < 5 {
                    return false;
                }
                let recent: Vec<&TaskPerformance> = self.task_history
                    .iter()
                    .filter(|t| t.agent == agent)
                    .rev()
                    .take(5)
                    .collect();
                
                if recent.len() < 5 {
                    return false;
                }
                let recent_success: f32 = recent.iter().filter(|t| t.success).count() as f32 / recent.len() as f32;
                recent_success < threshold
            })
            .unwrap_or(false)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_record_and_query() {
        let mut learner = DelegationLearner::new();
        learner.record_outcome("hephaestus", "build", true, 0.9, 5000);
        learner.record_outcome("hephaestus", "build", true, 0.8, 3000);
        learner.record_outcome("oracle", "review", true, 1.0, 2000);
        
        let perf = learner.get_performance("hephaestus").unwrap();
        assert!(perf.total_tasks == 2);
        assert!(perf.success_rate > 0.5);
    }

    #[test]
    fn test_select_best_agent() {
        let mut learner = DelegationLearner::new();
        learner.record_outcome("hephaestus", "build", false, 0.3, 10000);
        learner.record_outcome("oracle", "build", true, 1.0, 1000);
        
        let best = learner.select_best_agent("build");
        assert!(best.is_some());
        assert_eq!(best.unwrap(), "oracle");
    }

    #[test]
    fn test_detect_decay() {
        let mut learner = DelegationLearner::new();
        for _ in 0..5 {
            learner.record_outcome("hephaestus", "build", false, 0.2, 10000);
        }
        assert!(learner.detect_decay("hephaestus", 0.5));
    }
}
