# Master Code Quality Gap Report

**Generated:** 2026-04-09
**Scope:** All packages/ packages (~863 Python files)

---

## Executive Summary

| Package | Bare except: | print() | Missing Types | Hardcoded | Missing Error |
|---------|-------------|---------|---------------|-----------|----------------|
| orchestration | 3 | 8 | 15+ | 12 | 5 |
| intelligence | 14 | 54 | 40+ | 20+ | 12 |
| learning_engine | 0 | 6 | 6 | 10 | 3 |
| memory_core | 0 | 51 | 19+ | 12 | 4 |
| **TOTAL** | **17** | **119** | **80+** | **66** | **24** |

---

## Priority 1 - Critical (Blocking)

### 1.1 Bare except: Statements (17 total)

| Package | File | Line | Issue |
|---------|------|------|-------|
| orchestration | triggers/engine.py | 72 | `except Exception: pass` - silent |
| orchestration | triggers/router.py | 48 | `except Exception:` - no logging |
| orchestration | triggers.py | 148 | `except Exception:` - silent |
| intelligence | review/security_gate.py | 136 | `except Exception:` |
| intelligence | realtime_learner.py | 81 | `except Exception as e:` |
| intelligence | circuit_breaker.py | 237 | `except Exception as e:` |
| intelligence | error_recovery.py | 129 | `except Exception as retry_error:` |
| intelligence | fallback.py | 60, 232 | `except Exception as e:` (×2) |
| intelligence | health_monitor.py | 92 | `except Exception as e:` |
| intelligence | code_quality_tracker.py | 82,95,105,134 | `except Exception:` (×4) |
| intelligence | request_recorder.py | 295 | `except Exception as e:` |
| intelligence | agent_optimizer.py | 209 | `except Exception as e:` |

### 1.2 Silent Error Handling (pass blocks)

| File | Line | Issue |
|------|------|-------|
| triggers/engine.py | 72 | Silent pass |
| triggers.py | 148 | Silent return {} |
| db.py (learning_engine) | 101-102, 111-112 | Silent pass |
| db.py (learning_engine) | 243-244 | Silent pass |

---

## Priority 2 - High

### 2.1 print() Statements → Logging (119 total)

**intelligence package (54):**
- benchmark.py (91-231) - most critical
- router/local_model.py (284-289)
- router/keyword.py (164)
- delegation_logger.py (287, 290)
- result_checker.py (184)
- review/triage.py (128)
- review/security_gate.py (154)
- routing_context.py (74)

**memory_core package (51):**
- config.py (16, 335-336, 564-598)
- learning_config.py (174-186)
- health_monitor.py (637-641)
- migrations/* (multiple)

**orchestration package (8):**
- tool_categories.py (693-728) - __main__ block
- style_learner_integration.py (375-408) - __main__ block

**learning_engine package (6):**
- routing/confidence.py (53-63)
- meta/maml.py (213-248)
- meta/ewc.py (84-111)

### 2.2 Missing Type Hints (80+)

**intelligence (40+):**
- triggers/patterns.py, multi_agent_coordinator.py, realtime_learner.py, error_recovery.py, predictive_router.py, message_queue.py, agent_optimizer.py

**memory_core (19+):**
- router.py: all _get_*_retriever() methods
- mcp_server.py: _get_router(), recall_session()

**orchestration (15+):**
- triggers/engine.py, triggers/router.py, triggers.py, tasks/dispatcher.py, tool_cache.py, circuit_breaker.py

---

## Priority 3 - Medium

### 3.1 Hardcoded Values (66+)

| File | Value | Should Be |
|------|-------|-----------|
| triggers/router.py:28 | _RATE_LIMIT_WINDOW_SECONDS: 300 | Configurable |
| triggers/router.py:232,376 | > 60 (toast cooldown) | Configurable |
| triggers.py:25 | DEFAULT_DB_PATH | Configurable |
| triggers/patterns.py:21-22 | min_occurrences=3, min_success_rate=0.7 | Configurable |
| load_balancer.py:158 | _current_workers=3 | Configurable |
| context_compact.py:69 | context_window=32768 | Configurable |
| budget_tracker.py:87 | default_budget=100000 | Configurable |

### 3.2 Missing Error Handling (24)

| Package | File | Issue |
|---------|------|-------|
| orchestration | triggers/router.py:175 | MetricsStore without null check |
| orchestration | tasks/lifecycle.py:402 | File write without try/except |
| intelligence | db.py:37-43 | Silent RuntimeError pass |
| intelligence | routing_context.py:31-32 | Silent JSON error pass |
| intelligence | load_balancer.py:353-356 | Silent exception pass |
| learning_engine | db.py:84-86 | sqlite3.connect without try/except |
| memory_core | mcp_server.py:185-196 | SQLite without transaction |

---

## Priority 4 - Low

### 4.1 Any Type Usages (13+)

| File | Current | Suggested |
|------|---------|-----------|
| error_recovery.py:105 | `fallback_result: Any` | `Optional[T]` |
| error_recovery.py:121,135,157,162 | return `Any` | Generic return |
| interceptor.py:100,143 | `-> Any` | Specific type |
| load_balancer.py:130,411 | `message_queue: Any` | Specific type |
| router.py (memory_core) | MemoryResult.content: Any | Specific type |

### 4.2 Missing Docstrings (15+)

- router/keyword.py: max_level(), main()
- load_balancer.py: Multiple functions
- triggers/patterns.py: _extract_phrases()
- routing_context.py: generate_routing_context()

### 4.3 Duplicate Code Patterns

- to_dict()/to_json() duplicated across load_balancer.py (4 dataclasses), agent_optimizer.py, scoring/dynamic.py
- Lazy-loader pattern repeated 5+ times in router.py

---

## Fix Strategy

### Wave 1: Critical (Bare except + Silent Errors)
- Fix all 17 bare except: statements
- Fix all silent pass blocks

### Wave 2: High (print() → logging + Types)
- Convert print() to logger.debug/info
- Add return type annotations to public functions

### Wave 3: Medium (Hardcoded + Error Handling)
- Extract hardcoded values to config/constants
- Add try/except with proper error handling

### Wave 4: Low (Refactoring)
- Replace Any with specific types
- Add missing docstrings
- Create SerializableMixin base class
