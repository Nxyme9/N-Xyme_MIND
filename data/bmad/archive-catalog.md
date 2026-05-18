# Archive Package Catalog

**Generated**: 2026-05-17
**Source**: `archive/data_chaos/data_chaos/packages/`
**Total Lines**: ~83,000

---

## learning_engine/ (137 files)

RL, self-learning, prompt evolution, routing optimization

### Root Files
- `advanced_learning.py` — Advanced learning algorithms
- `benchmark.py` — Performance benchmarks
- `config.py` — Configuration management
- `cross_session_transfer.py` — Cross-session knowledge transfer
- `db.py` — Database layer
- `event_bus.py` — Event-driven communication
- `__init__.py` — Package init
- `mcp_server.py` — MCP server interface
- `memory_bridge.py` — Memory integration bridge
- `outcome_logger.py` — Outcome tracking
- `prompt_evolution.py` — Prompt optimization/evolution
- `rl_integration.py` — RL system integration
- `schemas.py` — Data schemas
- `self_correction.py` — Self-correction mechanisms
- `self_learning.py` — Self-learning core
- `session_hooks.py` — Session lifecycle hooks
- `sica_style.py` — SICA-style learning
- `signals.py` — Signal processing
- `skill_lifecycle.py` — Skill lifecycle management
- `skill_registry.py` — Skill registry
- `task_wrapper.py` — Task wrapping utilities
- `test_adaptive_router.py` — Adaptive router tests
- `test_qlearning.py` — Q-learning tests

### analytics/
- `__init__.py`
- `metrics.py` — Learning metrics

### bridges/
- `__init__.py`
- `outcome_to_memory_bridge.py` — Outcome-to-memory pipeline

### delegation/
- `db.py` — Delegation learning DB
- `__init__.py`
- `learner.py` — Delegation pattern learner

### embeddings/
- `__init__.py`
- `model_cache.py` — Embedding model cache

### intent_vectors/
- `builder.py` — Intent vector builder
- `__init__.py`

### meta/ (Meta-learning)
- `active.py` — Active meta-learning
- `ewc.py` — Elastic Weight Consolidation
- `__init__.py`
- `maml.py` — Model-Agnostic Meta-Learning
- `strategy_selector.py` — Meta-learning strategy selection

### migrations/
- `migrate_routing_data.py` — Routing data migration

### models/
- `__init__.py`
- `serializer.py` — Model serialization

### rl/ (Reinforcement Learning)
- `bandits.py` — Multi-armed bandits
- `complexity_adapter.py` — Complexity-based adaptation
- `double_dqn.py` — Double DQN implementation
- `__init__.py`
- `policy.py` — RL policy definitions
- `q_learning.py` — Q-learning implementation
- `rewards.py` — Reward function definitions
- `thompson_sampling.py` — Thompson sampling

### routing/
- `ab_testing.py` — A/B testing for routes
- `adaptive_router.py` — Adaptive routing
- `confidence.py` — Confidence scoring
- `counterfactual.py` — Counterfactual analysis
- `__init__.py`
- `multi_reward_router.py` — Multi-reward routing
- `optimizer.py` — Route optimizer
- `outcome_hook.py` — Outcome feedback hook

### tool_patterns/
- `analyzer.py` — Tool pattern analyzer
- `__init__.py`

---

## memory_core/ (116 files)

Tier manager, cognitive models, stores, retrievers

### Root Files
- `config.py` — Memory configuration
- `conflict_resolver.py` — Memory conflict resolution
- `connectors.py` — Store connectors
- `daemon.py` — Memory daemon
- `distributed_sync.py` — Distributed synchronization
- `health_monitor.py` — Memory health monitoring
- `health.py` — Health checks
- `__init__.py` — Package init
- `knowledge_graph.py` — Knowledge graph
- `learning_config.py` — Learning configuration
- `mcp_server.py` — MCP server interface
- `memory_manager.py` — Core memory manager
- `registry.py` — Memory registry
- `reranker.py` — Result reranking
- `router.py` — Memory routing
- `schemas.py` — Data schemas
- `self_healer.py` — Self-healing mechanisms
- `semantic_cache.py` — Semantic caching
- `session_memory.py` — Session-scoped memory
- `setup.py` — Setup utilities
- `sleep_engine.py` — Sleep consolidation engine
- `tier1_micro_compact.py` — Tier 1 micro compaction
- `tier2_summarizer.py` — Tier 2 summarization
- `tier_manager.py` — Tier management
- `two_phase_memory.py` — Two-phase memory system

### cognitive/ (Cognitive Models)
- `forgetting.py` — Forgetting curve model
- `__init__.py`
- `priority.py` — Memory priority scoring
- `reconsolidation.py` — Memory reconsolidation
- `retention.py` — Retention modeling
- `sleep_engine.py` — Cognitive sleep engine
- `trust.py` — Trust scoring

### core/
- `forgetting.py` — Core forgetting implementation
- `sleep_cycle.py` — Sleep cycle management

### indexing/
- `chunker.py` — Text chunking
- `__init__.py`
- `scanner.py` — File/content scanner

### migrations/
- `__init__.py`
- `migrate_nx_openmore.py` — NX/OpenMore migration
- `migrate_nxyme_catalyst.py` — Catalyst migration
- `migrate_sisyphus_graphs.py` — Sisyphus graph migration
- `migrate_sisyphus_memory.py` — Sisyphus memory migration
- `migrate_sisyphus_session.py` — Sisyphus session migration

### retrievers/
- `fusion.py` — Fusion retriever (hybrid)
- `hindsight.py` — Hindsight retrieval
- `__init__.py`
- `keyword.py` — Keyword retriever
- `pipeline.py` — Retrieval pipeline
- `reranker.py` — Retriever reranker
- `semantic.py` — Semantic retriever

### sessions/
- `archiver.py` — Session archiver
- `context.py` — Session context
- `__init__.py`
- `lifecycle.py` — Session lifecycle
- `session_capture.py` — Session capture

### stores/
- `base.py` — Base store interface
- `file_store.py` — File-based store
- `graph_store.py` — Graph store
- `__init__.py`
- `lance_store.py` — LanceDB store
- `relational_store.py` — Relational (SQLite) store
- `session_store.py` — Session store
- `vector_store.py` — Vector store (ChromaDB)

---

## intelligence/ (1838 files — includes venv)

Intent predictor, delegation learner, circuit breaker, routing

### Root Files
- `agent_optimizer.py` — Agent performance optimizer
- `benchmark.py` — Intelligence benchmarks
- `budget_tracker.py` — Token/budget tracking
- `circuit_breaker.py` — Circuit breaker pattern
- `code_quality_tracker.py` — Code quality metrics
- `context_compact.py` — Context compaction
- `context_manager.py` — Context management
- `context_optimizer.py` — Context optimization
- `db.py` — Database layer
- `delegation_learner.py` — Delegation pattern learning
- `delegation_logger.py` — Delegation logging
- `error_recovery.py` — Error recovery
- `fallback.py` — Fallback handling
- `health_ai.py` — AI health monitoring
- `health_monitor.py` — System health monitor
- `health_recovery.py` — Health recovery
- `__init__.py` — Package init
- `intent_predictor.py` — Intent prediction
- `load_balancer.py` — Load balancing
- `mcp_server.py` — MCP server interface
- `message_queue.py` — Message queue
- `multi_agent_coordinator.py` — Multi-agent coordination
- `permission_engine.py` — Permission checking
- `predictive_router.py` — Predictive routing
- `realtime_learner.py` — Real-time learning
- `request_recorder.py` — Request recording
- `result_checker.py` — Result validation
- `routing_context.py` — Routing context
- `schemas.py` — Data schemas
- `skill_registry.py` — Skill registry
- `tool_contract.py` — Tool contracts

### circuit_breaker/
- `circuit_breaker_rust.py` — Rust bridge for circuit breaker

### delegation/
- `communication.py` — Inter-agent communication
- `context_sharing.py` — Context sharing between agents
- `decomposer.py` — Task decomposition
- `__init__.py`
- `logger.py` — Delegation logger

### memory_search/
- `__init__.py`
- `mcp_server.py` — Memory search MCP server
- `py_bridge.py` — Python bridge

### review/
- `__init__.py`
- `security_gate.py` — Security review gate
- `triage.py` — Issue triage

### router/
- `__init__.py`
- `keyword.py` — Keyword-based routing
- `local_model.py` — Local model routing
- `memory.py` — Memory-based routing
- `ml.py` — ML-based routing
- `router_rust.py` — Rust bridge for router
- `semantic_classifier.py` — Semantic classification
- `trigger.py` — Trigger-based routing
- `unified.py` — Unified router

### scoring/
- `dynamic.py` — Dynamic scoring
- `__init__.py`
- `scorer_rust.py` — Rust bridge for scorer
- `token_estimator.py` — Token estimation

### templates/
- `__init__.py`
- `prompts.py` — Prompt templates

### triggers/
- `__init__.py`
- `patterns.py` — Trigger patterns

### middleware/
- `__init__.py`
- `interceptor.py` — Request interceptor
- `sandbox.py` — Sandbox execution

---

## training/ (31 files)

Training scripts, dataset generators, LoRA training

- `benchmark_chain.py` — Benchmark chain runner
- `convert_gguf.py` — GGUF format conversion
- `generate_78_tools_complete.py` — Tool dataset generator (complete)
- `generate_78_tools_dataset.py` — Tool dataset generator
- `generate_78_tools_v3.py` — Tool dataset generator v3
- `generate_correct_training_data.py` — Correct training data generator
- `generate_exact_training_data.py` — Exact training data generator
- `generate_from_sequences.py` — Sequence-based generator
- `generate_training_from_system.py` — System-driven training data
- `gguf_to_hf.py` — GGUF to HuggingFace conversion
- `pipeline_automator.py` — Training pipeline automation
- `quick_train.py` — Quick training script
- `test_inference.py` — Inference testing
- `training_trigger.py` — Training trigger
- `train_rosetta_lora.py` — Rosetta LoRA training
- `train_rosetta.py` — Rosetta training
- `train_rosetta_unified.py` — Unified Rosetta training

---

## infrastructure/ (223 files)

Proxy, resilience, benchmarks, monitoring, VPN

### Root Files
- `analytics.py` — Analytics engine
- `backup_manager.py` — Backup management
- `cache_service.py` — Caching service
- `cloud_sync.py` — Cloud synchronization
- `context_injector.py` — Context injection
- `decision_tracker.py` — Decision tracking
- `delta_manifest.py` — Delta manifest
- `dependency_checker.py` — Dependency checking
- `diminishing_returns.py` — Diminishing returns analysis
- `export_service.py` — Export service
- `file_indexer.py` — File indexing
- `__init__.py` — Package init
- `log_rotation.py` — Log rotation
- `multimodal_handler.py` — Multimodal handling
- `multimodal_service.py` — Multimodal service
- `performance_profiler.py` — Performance profiling
- `project_versioning.py` — Project versioning
- `resource_monitor.py` — Resource monitoring
- `startup_optimizer.py` — Startup optimization
- `system_utils.py` — System utilities
- `webhook_dlq.py` — Webhook dead letter queue

### config/
- `config_manager.py` — Configuration manager
- `config_service.py` — Configuration service
- `feature_flags.py` — Feature flags
- `validation_service.py` — Config validation
- `verification_engine.py` — Config verification

### cost/
- `cost_optimizer.py` — Cost optimization
- `cost_tracker_mcp.py` — Cost tracking MCP
- `tracker.py` — Cost tracker

### monitoring/
- `anomaly_detection.py` — Anomaly detection
- `metrics_collector.py` — Metrics collection
- `metrics.py` — Metrics definitions
- `telemetry.py` — Telemetry
- `telemetry_service.py` — Telemetry service

### network/
- `__init__.py`
- `socks5_transport.py` — SOCKS5 transport
- `vpn_manager.py` — VPN management
- `vpn_rotator.py` — VPN rotation

### proxy/ (40 files)
- `ab_testing.py` — A/B testing
- `agent_preferences.py` — Agent preference learning
- `api_key_pool.py` — API key pooling
- `connection_pool.py` — Connection pooling
- `cost_optimizer.py` — Proxy cost optimizer
- `dashboard.py` — Proxy dashboard
- `dead_letter_queue.py` — Dead letter queue
- `feedback.py` — Feedback collection
- `health_monitor.py` — Proxy health monitor
- `__init__.py`
- `intelligent_router.py` — Intelligent routing
- `key_notifier.py` — Key change notifications
- `learning_engine.py` — Proxy learning engine
- `lru_cache.py` — LRU caching
- `__main__.py` — Entry point
- `mcp_server.py` — Proxy MCP server
- `observability.py` — Observability
- `openai_proxy.py` — OpenAI proxy
- `optimizer.py` — Proxy optimizer
- `qwen_rate_limit.py` — Qwen rate limiting
- `rate_optimizer.py` — Rate optimization
- `request_validator.py` — Request validation
- `router_brain.py` — Router brain
- `routing_strategies.py` — Routing strategies
- `server.py` — Proxy server
- `simple_mcp_server.py` — Simple MCP server
- `stall_detector.py` — Stall detection
- `tuple_rate_limiter.py` — Tuple rate limiting
- `vpn_ip_pool.py` — VPN IP pool
- `vpn_rotator.py` — VPN rotation

### resilience/
- `circuit_breaker.py` — Circuit breaker
- `error_handler.py` — Error handling
- `__init__.py`
- `rate_limiter.py` — Rate limiting
- `retry_handler.py` — Retry handling

### spine/
- `cli.py` — CLI interface
- `config.py` — Spine configuration
- `fallback.py` — Fallback handling
- `health.py` — Health checks
- `__init__.py`
- `run_tracker.py` — Run tracking
- `spine.py` — Core spine
- `tests/__init__.py`
- `tests/test_config.py`
- `tests/test_fallback.py`
- `tests/test_health.py`
- `tests/test_spine.py`

### utils/
- `datetime_utils.py` — Date/time utilities
- `hash_service.py` — Hashing service
- `serialization.py` — Serialization utilities

### vpn_rotation/
- `cli.py` — CLI interface
- `health.py` — Health checks
- `__init__.py`
- `manager.py` — VPN manager
- `models.py` — Data models
- `provider.py` — Provider abstraction
- `router.py` — VPN router
- `wireguard_native.py` — WireGuard native
- `wireproxy.py` — WireProxy integration

---

## ChromaDB Status

| Collection | Documents | Vector Dim |
|---|---|---|
| `file_embeddings` | 763,644 | 768 |

**Path**: `archive/data_chaos/data_chaos/context/memory/file_chroma`
**Backend**: PersistentClient (local disk)

---

## Key ML Components for Rust Port

### Priority 1 (Core Intelligence)
- `intelligence/circuit_breaker.py` → `ml/circuit_breaker.rs`
- `intelligence/intent_predictor.py` → `ml/intent_predictor.rs`
- `intelligence/delegation_learner.py` → `ml/delegation_learner.rs`
- `intelligence/agent_optimizer.py` → `ml/agent_optimizer.rs`

### Priority 2 (Learning Engine)
- `learning_engine/rl/q_learning.py` → `ml/q_learning.rs`
- `learning_engine/prompt_evolution.py` → `ml/prompt_evolution.rs`
- `learning_engine/self_learning.py` → `ml/self_learning.rs`
- `learning_engine/rl/double_dqn.py` → `ml/double_dqn.rs`

### Priority 3 (Memory)
- `memory_core/tier_manager.py` → future `memory/` crate
- `memory_core/cognitive/` → future `memory/` crate
- `memory_core/retrievers/` → future `memory/` crate
