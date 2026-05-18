use std::collections::HashMap;

#[derive(Debug, Clone)]
pub struct TaskRecord {
    pub agent: String,
    pub task: String,
    pub success: bool,
    pub quality: f32,
    pub timestamp: std::time::Instant,
}

pub struct AgentOptimizer {
    task_history: HashMap<String, Vec<TaskRecord>>,
    decay_threshold: f32,
    recency_weight: f32,
}

impl AgentOptimizer {
    pub fn new(decay_threshold: f32, recency_weight: f32) -> Self {
        Self {
            task_history: HashMap::new(),
            decay_threshold,
            recency_weight,
        }
    }

    pub fn track_performance(&mut self, agent: &str, task: &str, success: bool, quality: f32) {
        let entry = self.task_history.entry(agent.to_string()).or_default();
        entry.push(TaskRecord {
            agent: agent.to_string(),
            task: task.to_string(),
            success,
            quality,
            timestamp: std::time::Instant::now(),
        });
    }

    pub fn detect_decay(&self, agent: &str) -> bool {
        let records = match self.task_history.get(agent) {
            Some(r) => r,
            None => return false,
        };

        if records.len() < 5 {
            return false;
        }

        let recent: Vec<&TaskRecord> = records.iter().rev().take(5).collect();
        let recent_success: f32 = recent.iter().filter(|r| r.success).count() as f32 / recent.len() as f32;
        recent_success < self.decay_threshold
    }

    pub fn recommend_agent(&self, task_type: &str) -> Option<String> {
        let mut scores: HashMap<&str, f32> = HashMap::new();

        for (agent, records) in &self.task_history {
            let relevant: Vec<&TaskRecord> = records.iter().filter(|r| r.task == task_type).collect();
            if relevant.is_empty() {
                continue;
            }

            let mut score = 0.0;
            let total = relevant.len() as f32;

            for record in &relevant {
                let recency = if record.success { 1.0 } else { 0.0 };
                score += self.recency_weight * recency + (1.0 - self.recency_weight) * record.quality;
            }

            scores.insert(agent, score / total);
        }

        scores
            .into_iter()
            .max_by(|(_, a), (_, b)| a.partial_cmp(b).unwrap())
            .map(|(agent, _)| agent.to_string())
    }

    pub fn get_agent_success_rate(&self, agent: &str) -> f32 {
        let records = match self.task_history.get(agent) {
            Some(r) => r,
            None => return 0.0,
        };

        if records.is_empty() {
            return 0.0;
        }

        let successes = records.iter().filter(|r| r.success).count() as f32;
        successes / records.len() as f32
    }
}

impl Default for AgentOptimizer {
    fn default() -> Self {
        Self::new(0.15, 0.7)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_track_and_recommend() {
        let mut opt = AgentOptimizer::default();
        opt.track_performance("hephaestus", "build", true, 0.9);
        opt.track_performance("hephaestus", "build", true, 0.8);
        opt.track_performance("oracle", "review", true, 1.0);
        
        let rate = opt.get_agent_success_rate("hephaestus");
        assert_eq!(rate, 1.0);
    }

    #[test]
    fn test_detect_decay_threshold() {
        let mut opt = AgentOptimizer::default();
        for _ in 0..6 {
            opt.track_performance("hephaestus", "build", false, 0.1);
        }
        assert!(opt.detect_decay("hephaestus"));
    }

    #[test]
    fn test_default_threshold() {
        let opt = AgentOptimizer::default();
        assert_eq!(opt.decay_threshold, 0.15);
        assert_eq!(opt.recency_weight, 0.7);
    }
}
