use std::collections::HashMap;

#[derive(Debug, Clone)]
pub struct IntentPrediction {
    pub intent: String,
    pub confidence: f32,
    pub agent: String,
    pub tool: String,
}

impl IntentPrediction {
    pub fn new(intent: &str, confidence: f32, agent: &str, tool: &str) -> Self {
        Self {
            intent: intent.to_string(),
            confidence,
            agent: agent.to_string(),
            tool: tool.to_string(),
        }
    }
}

pub struct IntentPredictor {
    patterns: HashMap<String, Vec<String>>,
    weights: HashMap<String, f32>,
    training_data: Vec<(String, String)>,
}

impl IntentPredictor {
    pub fn new() -> Self {
        let mut patterns = HashMap::new();
        patterns.insert("build".to_string(), vec!["create".to_string(), "generate".to_string(), "write".to_string(), "implement".to_string(), "code".to_string()]);
        patterns.insert("search".to_string(), vec!["find".to_string(), "lookup".to_string(), "search".to_string(), "query".to_string(), "where".to_string()]);
        patterns.insert("fix".to_string(), vec!["fix".to_string(), "bug".to_string(), "error".to_string(), "broken".to_string(), "issue".to_string()]);
        patterns.insert("therapy".to_string(), vec!["therapy".to_string(), "therapist".to_string(), "feel".to_string(), "anxiety".to_string(), "stress".to_string(), "adhd".to_string()]);
        patterns.insert("plan".to_string(), vec!["plan".to_string(), "strategy".to_string(), "roadmap".to_string(), "epic".to_string(), "story".to_string()]);
        patterns.insert("review".to_string(), vec!["review".to_string(), "audit".to_string(), "check".to_string(), "inspect".to_string(), "analyze".to_string()]);
        patterns.insert("research".to_string(), vec!["research".to_string(), "learn".to_string(), "study".to_string(), "investigate".to_string(), "explore".to_string()]);

        Self {
            patterns,
            weights: HashMap::new(),
            training_data: Vec::new(),
        }
    }

    pub fn predict(&self, input: &str) -> IntentPrediction {
        let input_lower = input.to_lowercase();
        let mut best_match = String::from("general");
        let mut best_score = 0.0f32;
        let mut best_agent = String::from("sisyphus");
        let mut best_tool = String::from("ask");

        for (intent, keywords) in &self.patterns {
            let score = self.score_intent(&input_lower, keywords);
            let weighted_score = score * self.weights.get(intent).unwrap_or(&1.0);

            if weighted_score > best_score {
                best_score = weighted_score;
                best_match = intent.clone();
                let (agent, tool) = self.get_routing(intent);
                best_agent = agent;
                best_tool = tool;
            }
        }

        IntentPrediction::new(&best_match, best_score, &best_agent, &best_tool)
    }

    fn score_intent(&self, input: &str, keywords: &[String]) -> f32 {
        let mut matches = 0;
        for keyword in keywords {
            if input.contains(keyword) {
                matches += 1;
            }
        }
        if keywords.is_empty() {
            return 0.0;
        }
        matches as f32 / keywords.len() as f32
    }

    fn get_routing(&self, intent: &str) -> (String, String) {
        match intent {
            "build" => ("hephaestus".to_string(), "build".to_string()),
            "search" => ("sisyphus".to_string(), "memory_search".to_string()),
            "fix" => ("hephaestus".to_string(), "fix".to_string()),
            "therapy" => ("kairos".to_string(), "therapy".to_string()),
            "plan" => ("prometheus".to_string(), "plan".to_string()),
            "review" => ("momus".to_string(), "review".to_string()),
            "research" => ("librarian".to_string(), "research".to_string()),
            _ => ("sisyphus".to_string(), "ask".to_string()),
        }
    }

    pub fn train(&mut self, input: &str, intent: &str) {
        self.training_data.push((input.to_string(), intent.to_string()));
        let entry = self.weights.entry(intent.to_string()).or_insert(0.0);
        *entry += 0.1;
    }

    pub fn get_available_intents(&self) -> Vec<&str> {
        self.patterns.keys().map(|s| s.as_str()).collect()
    }

    pub fn confidence(&self) -> f32 {
        if self.training_data.is_empty() {
            return 0.0;
        }
        (self.training_data.len() as f32).min(1.0) / 100.0
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_predict_build_intent() {
        let predictor = IntentPredictor::new();
        let result = predictor.predict("create a new Rust function");
        assert_eq!(result.intent, "build");
        assert_eq!(result.agent, "hephaestus");
    }

    #[test]
    fn test_predict_search_intent() {
        let predictor = IntentPredictor::new();
        let result = predictor.predict("search for the query result location");
        assert_eq!(result.intent, "search");
    }

    #[test]
    fn test_predict_therapy_intent() {
        let predictor = IntentPredictor::new();
        let result = predictor.predict("I feel anxious about the deadline");
        assert_eq!(result.intent, "therapy");
        assert_eq!(result.agent, "kairos");
    }

    #[test]
    fn test_training_updates_weights() {
        let mut predictor = IntentPredictor::new();
        predictor.train("do something", "build");
        assert!(predictor.training_data.len() == 1);
    }
}
