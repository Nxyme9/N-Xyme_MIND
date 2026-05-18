use std::collections::HashMap;

#[derive(Debug, Clone, Hash, Eq, PartialEq)]
pub enum ActionType {
    RouteToSisyphus,
    RouteToHephaestus,
    RouteToKairos,
    RouteToOracle,
    RouteToMemory,
    RouteToMomus,
    RouteToPrometheus,
    RouteToExplore,
    RouteToLibrarian,
}

impl ActionType {
    pub fn all() -> Vec<ActionType> {
        vec![
            ActionType::RouteToSisyphus,
            ActionType::RouteToHephaestus,
            ActionType::RouteToKairos,
            ActionType::RouteToOracle,
            ActionType::RouteToMemory,
            ActionType::RouteToMomus,
            ActionType::RouteToPrometheus,
            ActionType::RouteToExplore,
            ActionType::RouteToLibrarian,
        ]
    }

    pub fn name(&self) -> &str {
        match self {
            ActionType::RouteToSisyphus => "sisyphus",
            ActionType::RouteToHephaestus => "hephaestus",
            ActionType::RouteToKairos => "kairos",
            ActionType::RouteToOracle => "oracle",
            ActionType::RouteToMemory => "memory",
            ActionType::RouteToMomus => "momus",
            ActionType::RouteToPrometheus => "prometheus",
            ActionType::RouteToExplore => "explore",
            ActionType::RouteToLibrarian => "librarian",
        }
    }
}

#[derive(Debug, Clone)]
pub struct QState {
    pub features: Vec<f32>,
    pub label: String,
}

impl QState {
    pub fn new(features: Vec<f32>, label: &str) -> Self {
        Self {
            features,
            label: label.to_string(),
        }
    }

    pub fn from_text(text: &str) -> Self {
        // Simple hash-based state representation
        let input = text.to_lowercase();
        let mut features = Vec::with_capacity(16);
        for i in 0..16 {
            features.push(input.chars().nth(i).map(|c| c as i32 as f32 / 256.0).unwrap_or(0.0));
        }
        let label = Self::classify(&input);
        Self { features, label }
    }

    fn classify(input: &str) -> String {
        if input.contains("build") || input.contains("code") || input.contains("create") {
            "build".to_string()
        } else if input.contains("search") || input.contains("find") {
            "search".to_string()
        } else if input.contains("fix") || input.contains("bug") {
            "fix".to_string()
        } else if input.contains("therapy") || input.contains("anxiety") {
            "therapy".to_string()
        } else if input.contains("plan") || input.contains("strategy") {
            "plan".to_string()
        } else if input.contains("review") || input.contains("audit") {
            "review".to_string()
        } else if input.contains("research") {
            "research".to_string()
        } else {
            "general".to_string()
        }
    }
}

pub struct QLearningEngine {
    q_table: HashMap<String, HashMap<ActionType, f32>>,
    learning_rate: f32,
    discount_factor: f32,
    epsilon: f32,
    epsilon_decay: f32,
    min_epsilon: f32,
    total_updates: u64,
}

impl QLearningEngine {
    pub fn new(learning_rate: f32, discount_factor: f32, epsilon: f32) -> Self {
        Self {
            q_table: HashMap::new(),
            learning_rate,
            discount_factor,
            epsilon,
            epsilon_decay: 0.995,
            min_epsilon: 0.01,
            total_updates: 0,
        }
    }

    pub fn get_q_value(&self, state: &QState, action: &ActionType) -> f32 {
        self.q_table
            .get(&state.label)
            .and_then(|actions| actions.get(action))
            .copied()
            .unwrap_or(0.0)
    }

    pub fn update(&mut self, state: &QState, action: &ActionType, reward: f32, next_state: &QState) {
        let current_q = self.get_q_value(state, action);
        let max_next_q = ActionType::all()
            .iter()
            .map(|a| self.get_q_value(next_state, a))
            .fold(f32::NEG_INFINITY, f32::max);
        let td_target = reward + self.discount_factor * max_next_q;
        let td_error = td_target - current_q;
        let new_q = current_q + self.learning_rate * td_error;

        self.q_table
            .entry(state.label.clone())
            .or_default()
            .insert(action.clone(), new_q);

        self.total_updates += 1;
        if self.total_updates % 100 == 0 {
            self.epsilon = (self.epsilon * self.epsilon_decay).max(self.min_epsilon);
        }
    }

    pub fn choose_action(&self, state: &QState) -> ActionType {
        let mut rng = rand::thread_rng();
        if rand::Rng::gen::<f32>(&mut rng) < self.epsilon {
            let actions = ActionType::all();
            let idx = rand::Rng::gen_range(&mut rng, 0..actions.len());
            return actions[idx].clone();
        }

        let actions = ActionType::all();
        let mut best_action = actions[0].clone();
        let mut best_value = self.get_q_value(state, &best_action);

        for action in &actions {
            let value = self.get_q_value(state, action);
            if value > best_value {
                best_value = value;
                best_action = action.clone();
            }
        }

        best_action
    }

    pub fn get_epsilon(&self) -> f32 {
        self.epsilon
    }

    pub fn get_total_updates(&self) -> u64 {
        self.total_updates
    }
}

impl Default for QLearningEngine {
    fn default() -> Self {
        Self::new(0.1, 0.9, 1.0)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_initial_q_values() {
        let engine = QLearningEngine::default();
        let state = QState::from_text("build something");
        let value = engine.get_q_value(&state, &ActionType::RouteToHephaestus);
        assert_eq!(value, 0.0);
    }

    #[test]
    fn test_update() {
        let mut engine = QLearningEngine::new(1.0, 0.9, 1.0);
        let state = QState::from_text("build something");
        let next_state = QState::from_text("success");
        engine.update(&state, &ActionType::RouteToHephaestus, 1.0, &next_state);
        let value = engine.get_q_value(&state, &ActionType::RouteToHephaestus);
        assert!(value > 0.0);
    }

    #[test]
    fn test_choose_action() {
        let engine = QLearningEngine::new(0.1, 0.9, 0.0);
        let state = QState::from_text("build something");
        let action = engine.choose_action(&state);
        assert!(ActionType::all().contains(&action));
    }

    #[test]
    fn test_epsilon_decay() {
        let mut engine = QLearningEngine::new(0.1, 0.9, 1.0);
        let state = QState::from_text("test");
        let next = QState::from_text("test2");
        for _ in 0..200 {
            engine.update(&state, &ActionType::RouteToSisyphus, 0.0, &next);
        }
        assert!(engine.get_epsilon() < 1.0);
    }
}
