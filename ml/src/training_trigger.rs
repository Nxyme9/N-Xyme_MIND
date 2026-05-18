use std::path::Path;
use std::fs;

pub struct TrainingTrigger {
    correction_path: String,
    threshold: u32,
}

impl TrainingTrigger {
    pub fn new() -> Self {
        Self {
            correction_path: "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/data/memory/corrections.jsonl".to_string(),
            threshold: 100,
        }
    }

    pub fn count_corrections(&self) -> u32 {
        let path = Path::new(&self.correction_path);
        if !path.exists() { return 0; }
        let content = match fs::read_to_string(path) { Ok(c) => c, Err(_) => return 0 };
        content.lines().count() as u32
    }

    pub fn should_trigger(&self) -> bool {
        self.count_corrections() >= self.threshold
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_count() {
        let t = TrainingTrigger::new();
        println!("Corrections: {}/{}", t.count_corrections(), t.threshold);
    }

    #[test]
    fn test_threshold() {
        let t = TrainingTrigger::new();
        assert!(!t.should_trigger(), "Need {} corrections, have {}", t.threshold, t.count_corrections());
    }
}
