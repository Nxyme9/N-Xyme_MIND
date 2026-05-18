use ml::circuit_breaker::CircuitBreakerRegistry;
use ml::delegation_learner::DelegationLearner;
use ml::intent_predictor::{IntentPrediction as MlIntentPrediction, IntentPredictor};
use ml::q_learning::{ActionType, QLearningEngine, QState};
use std::sync::Mutex;
use std::time::Duration;

static CIRCUIT_REGISTRY: std::sync::OnceLock<Mutex<CircuitBreakerRegistry>> = std::sync::OnceLock::new();
static INTENT_PREDICTOR: std::sync::OnceLock<Mutex<IntentPredictor>> = std::sync::OnceLock::new();
static DELEGATION_LEARNER: std::sync::OnceLock<Mutex<DelegationLearner>> = std::sync::OnceLock::new();
static Q_ENGINE: std::sync::OnceLock<Mutex<QLearningEngine>> = std::sync::OnceLock::new();

fn get_circuit_registry() -> &'static Mutex<CircuitBreakerRegistry> {
    CIRCUIT_REGISTRY.get_or_init(|| Mutex::new(CircuitBreakerRegistry::new(3, Duration::from_secs(120))))
}

fn get_intent_predictor() -> &'static Mutex<IntentPredictor> {
    INTENT_PREDICTOR.get_or_init(|| Mutex::new(IntentPredictor::new()))
}

fn get_delegation_learner() -> &'static Mutex<DelegationLearner> {
    DELEGATION_LEARNER.get_or_init(|| Mutex::new(DelegationLearner::new()))
}

fn get_q_engine() -> &'static Mutex<QLearningEngine> {
    Q_ENGINE.get_or_init(|| Mutex::new(QLearningEngine::new(0.1, 0.9, 0.1)))
}

pub struct IntentPrediction {
    pub intent: String,
    pub confidence: f32,
    pub agent: String,
    pub tool: String,
}

pub fn circuit_breaker_check(tool: &str) -> bool {
    let registry = get_circuit_registry();
    let mut guard = registry.lock().unwrap();
    guard.can_execute(tool)
}

pub fn record_circuit_success(tool: &str) {
    let registry = get_circuit_registry();
    registry.lock().unwrap().record_success(tool);
}

pub fn record_circuit_failure(tool: &str) {
    let registry = get_circuit_registry();
    registry.lock().unwrap().record_failure(tool);
}

pub fn predict_intent(query: &str) -> IntentPrediction {
    let predictor = get_intent_predictor();
    let guard = predictor.lock().unwrap();
    let result = guard.predict(query);
    IntentPrediction {
        intent: result.intent,
        confidence: result.confidence,
        agent: result.agent,
        tool: result.tool,
    }
}

pub fn predict_intent_agents(query: &str, min_score: f32) -> Vec<(String, f32)> {
    let predictor = get_intent_predictor();
    let guard = predictor.lock().unwrap();
    guard.predict_agents(query, min_score)
}

pub fn train_intent(input: &str, intent: &str) {
    let predictor = get_intent_predictor();
    let mut guard = predictor.lock().unwrap();
    guard.train(input, intent);
}

pub fn select_best_agent(task: &str) -> Option<String> {
    let learner = get_delegation_learner();
    let guard = learner.lock().unwrap();
    learner.select_best_agent(task)
}

pub fn record_delegation_outcome(agent: &str, task: &str, success: bool, quality: f32, duration_ms: u64) {
    let learner = get_delegation_learner();
    let mut guard = learner.lock().unwrap();
    guard.record_outcome(agent, task, success, quality, duration_ms);
}

pub fn update_q_state(state: &QState, action: &ActionType, reward: f32) {
    let engine = get_q_engine();
    let mut guard = engine.lock().unwrap();
    let next_state = QState::new(vec![0.0; state.features.len()]);
    guard.update(state, action, reward, &next_state);
}

pub fn update_q_state_with_next(state: &QState, action: &ActionType, reward: f32, next_state: &QState) {
    let engine = get_q_engine();
    let mut guard = engine.lock().unwrap();
    guard.update(state, action, reward, next_state);
}

pub fn choose_q_action(state: &QState) -> ActionType {
    let engine = get_q_engine();
    let guard = engine.lock().unwrap();
    guard.choose_action(state)
}

pub fn choose_q_action_available(state: &QState, available: &[ActionType]) -> Option<ActionType> {
    let engine = get_q_engine();
    let guard = engine.lock().unwrap();
    guard.choose_action_with_available(state, available)
}

pub fn get_q_value(state: &QState, action: &ActionType) -> f32 {
    let engine = get_q_engine();
    let guard = engine.lock().unwrap();
    guard.get_q_value(state, action)
}

pub fn track_agent_performance(agent: &str, task: &str, success: bool, quality: f32) {
    let optimizer = get_delegation_learner();
    let mut guard = optimizer.lock().unwrap();
    guard.record_outcome(agent, task, success, quality, 1000);
}

pub fn reset_ml_state() {
    if let Some(registry) = CIRCUIT_REGISTRY.get() {
        registry.lock().unwrap().reset_all();
    }
}
