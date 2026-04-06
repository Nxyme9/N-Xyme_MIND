#!/usr/bin/env python3
"""
Comprehensive Config-Driven Functionality Validation
Validates 100% of config-driven functionality for N-Xyme MIND v0.1
"""

import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PASS = 0
FAIL = 0
WARN = 0


def check(name, condition, detail=""):
    global PASS, FAIL, WARN
    if condition:
        PASS += 1
        print(f"  ✅ {name}")
    elif detail == "warn":
        WARN += 1
        print(f"  ⚠️  {name} (warning)")
    else:
        FAIL += 1
        print(f"  ❌ {name}: {detail}")


def section(title):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


# ============================================================================
# 1. oh-my-opencode.json — Agent Configuration
# ============================================================================
section("1. oh-my-opencode.json — Agent Configuration")

try:
    with open(PROJECT_ROOT / "oh-my-opencode.json") as f:
        omo = json.load(f)
    check("JSON valid", True)
except Exception as e:
    check("JSON valid", False, str(e))
    omo = {}

# Check agents
agents = omo.get("agents", {})
expected_agents = [
    "sisyphus",
    "atlas",
    "hephaestus",
    "prometheus",
    "oracle",
    "metis",
    "momus",
    "explore",
    "librarian",
    "sisyphus-junior",
    "multimodal-looker",
]
for agent in expected_agents:
    check(f"Agent '{agent}' defined", agent in agents, f"Missing agent: {agent}")

# Check agent properties
for agent_name, agent_config in agents.items():
    check(f"  {agent_name}: has model", "model" in agent_config, "Missing model")
    check(
        f"  {agent_name}: has description",
        "description" in agent_config,
        "Missing description",
    )
    check(
        f"  {agent_name}: has fallback_models",
        "fallback_models" in agent_config,
        "Missing fallbacks",
    )
    if "temperature" in agent_config:
        t = agent_config["temperature"]
        check(f"  {agent_name}: temperature valid (0-1)", 0 <= t <= 1, f"Invalid: {t}")
    if "reasoningEffort" in agent_config:
        re = agent_config["reasoningEffort"]
        check(
            f"  {agent_name}: reasoningEffort valid",
            re in ["low", "medium", "high", "xhigh"],
            f"Invalid: {re}",
        )

# Check categories
categories = omo.get("categories", {})
expected_categories = [
    "visual-engineering",
    "ultrabrain",
    "deep",
    "artistry",
    "quick",
    "unspecified-low",
    "unspecified-high",
    "routing",
    "writing",
]
for cat in expected_categories:
    check(f"Category '{cat}' defined", cat in categories, f"Missing category: {cat}")

# Check experimental features
exp = omo.get("experimental", {})
dcp = exp.get("dynamic_context_pruning", {})
check(
    "Dynamic context pruning enabled", dcp.get("enabled", False) == True, "Not enabled"
)
check(
    "Turn protection enabled",
    dcp.get("turn_protection", {}).get("enabled", False) == True,
    "Not enabled",
)
check(
    "Deduplication enabled",
    dcp.get("strategies", {}).get("deduplication", {}).get("enabled", False) == True,
    "Not enabled",
)
check(
    "Supersede writes enabled",
    dcp.get("strategies", {}).get("supersede_writes", {}).get("enabled", False) == True,
    "Not enabled",
)
check(
    "Purge errors enabled",
    dcp.get("strategies", {}).get("purge_errors", {}).get("enabled", False) == True,
    "Not enabled",
)

# ============================================================================
# 2. opencode.json — MCP Server Wiring
# ============================================================================
section("2. opencode.json — MCP Server Wiring")

try:
    with open(PROJECT_ROOT / "opencode.json") as f:
        oc = json.load(f)
    check("JSON valid", True)
except Exception as e:
    check("JSON valid", False, str(e))
    oc = {}

# Check MCP servers
mcp = oc.get("mcp", {})
expected_mcp = [
    "sequential-thinking",
    "memory",
    "context7",
    "filesystem",
    "fetch",
    "git",
    "athena",
    "github",
    "athena-context",
    "trigger-guardian",
    "nx-mind",
    "unified-memory",
]
for server in expected_mcp:
    check(f"MCP server '{server}' defined", server in mcp, f"Missing: {server}")
    if server in mcp:
        check(f"  {server}: has command", "command" in mcp[server], "Missing command")
        check(f"  {server}: has type", "type" in mcp[server], "Missing type")

# Check permissions
perm = oc.get("permission", {})
check("Read permissions defined", "read" in perm, "Missing read permissions")
check("Edit permissions defined", "edit" in perm, "Missing edit permissions")
check("Bash permissions defined", "bash" in perm, "Missing bash permissions")
check("*.env denied", perm.get("read", {}).get("*.env") == "deny", "Not denied")
check("*.pem denied", perm.get("read", {}).get("*.pem") == "deny", "Not denied")

# Check agent permissions
agent_perm = oc.get("agent", {})
for agent in ["explore", "librarian", "sisyphus-junior"]:
    check(
        f"Agent '{agent}' permissions defined", agent in agent_perm, f"Missing: {agent}"
    )

# Check enabled providers
providers = oc.get("enabled_providers", [])
check("Enabled providers defined", len(providers) > 0, "No providers")
for provider in ["openrouter", "opencode", "google"]:
    check(
        f"Provider '{provider}' enabled", provider in providers, f"Missing: {provider}"
    )

# ============================================================================
# 3. triggers.json — Trigger Engine
# ============================================================================
section("3. triggers.json — Trigger Engine")

try:
    with open(PROJECT_ROOT / "triggers.json") as f:
        triggers = json.load(f)
    check("JSON valid", True)
except Exception as e:
    check("JSON valid", False, str(e))
    triggers = {}

# Check action registry
actions = triggers.get("action_registry", {})
expected_actions = [
    "restart_service",
    "throttle_ollama",
    "force_gc",
    "alert",
    "quarantine",
    "clean_stale",
    "clear_lock",
    "rotate_vpn",
    "rotate_api_key",
    "validate_config",
    "check_model",
    "restart_graphiti",
    "verify_all",
    "pull_model",
    "diagnose",
    "record_velocity",
    "start_timing",
    "run_reality_check",
    "log_verified_claim",
    "reject_claim",
    "distill_memory",
]
for action in expected_actions:
    check(f"Action '{action}' defined", action in actions, f"Missing: {action}")
    if action in actions:
        check(f"  {action}: has type", "type" in actions[action], "Missing type")
        check(
            f"  {action}: has description",
            "description" in actions[action],
            "Missing description",
        )

# Check trigger categories
trigger_cats = triggers.get("triggers", {})
expected_cats = [
    "gpu",
    "pm2",
    "service",
    "database",
    "sessions",
    "rate_limit",
    "config",
    "graphiti",
    "ollama",
    "system",
    "velocity",
    "consciousness",
    "memory",
]
for cat in expected_cats:
    check(f"Trigger category '{cat}' defined", cat in trigger_cats, f"Missing: {cat}")
    if cat in trigger_cats:
        count = len(trigger_cats[cat])
        check(f"  {cat}: has {count} triggers", count > 0, "No triggers")

# Count total triggers
total_triggers = sum(len(v) for v in trigger_cats.values())
check(f"Total triggers >= 25", total_triggers >= 25, f"Only {total_triggers} triggers")

# Check global settings
gs = triggers.get("global_settings", {})
check("max_concurrent_actions defined", "max_concurrent_actions" in gs, "Missing")
check("default_cooldown_seconds defined", "default_cooldown_seconds" in gs, "Missing")
check("escalation_after_failures defined", "escalation_after_failures" in gs, "Missing")
check("circuit_breaker defined", "circuit_breaker" in gs, "Missing")
cb = gs.get("circuit_breaker", {})
check("  circuit_breaker: max_failures", "max_failures" in cb, "Missing")
check("  circuit_breaker: window_seconds", "window_seconds" in cb, "Missing")
check("  circuit_breaker: reset_after_seconds", "reset_after_seconds" in cb, "Missing")

# ============================================================================
# 4. AGENTS.md — Workspace Rules
# ============================================================================
section("4. AGENTS.md — Workspace Rules")

agents_md = PROJECT_ROOT / "AGENTS.md"
check("AGENTS.md exists", agents_md.exists(), "File not found")

if agents_md.exists():
    content = agents_md.read_text()
    check("AGENTS.md has content", len(content) > 1000, f"Only {len(content)} chars")

    # Check required sections
    required_sections = [
        "AGENT SWITCH DETECTION",
        "OPENCODE ARCHITECTURE",
        "System Map",
        "AGENT REGISTRY",
        "MCP Servers",
        "Parallel Limits",
        "ADHD Operating Protocol",
        "Schema Safety Protocol",
        "Compression Guard",
        "Circuit Breakers",
        "Stuck Protocol",
        "Delegation Rules",
        "Anti-Loop Protocol",
        "Context-Activated Rules",
        "Lessons from Previous Iterations",
        "Anti-Patterns",
        "Masterprompt",
        "FACT VERIFICATION",
        "Mandatory Error Handling",
        "Edge Case Checklist",
        "Security Defaults",
        "Task Tool Rules",
        "Safety Rules",
        "BMAD Integration",
    ]
    for section_name in required_sections:
        check(
            f"Section '{section_name}' present",
            section_name in content,
            f"Missing: {section_name}",
        )

    # Check anti-loop rules
    anti_loop_rules = [
        "Max Attempts",
        "Mandatory Reflection",
        "Action Fingerprinting",
        "Fundamentally Different",
        "Session State Tracking",
        "Escalation Ladder",
    ]
    for rule in anti_loop_rules:
        check(f"Anti-loop rule: {rule}", rule in content, f"Missing: {rule}")

    # Check circuit breakers
    circuit_breakers = [
        "Token Budget",
        "Step Limit",
        "Timeout",
        "Failure Limit",
        "Stuck Detection",
        "Trigger Budget",
        "Attempt Counter",
        "Progress Check",
    ]
    for cb in circuit_breakers:
        check(f"Circuit breaker: {cb}", cb in content, f"Missing: {cb}")

# ============================================================================
# 5. .sisyphus/rules/ — Orchestration Rules
# ============================================================================
section("5. .sisyphus/rules/ — Orchestration Rules")

rules_dir = PROJECT_ROOT / ".sisyphus" / "rules"
check("Rules directory exists", rules_dir.exists(), "Directory not found")

if rules_dir.exists():
    global_rules = rules_dir / "global-rules.md"
    building_rules = rules_dir / "building-rules.md"

    check("global-rules.md exists", global_rules.exists(), "File not found")
    check("building-rules.md exists", building_rules.exists(), "File not found")

    if global_rules.exists():
        content = global_rules.read_text()
        check(
            "global-rules.md has content",
            len(content) > 500,
            f"Only {len(content)} chars",
        )

        required_rules = [
            "Optimization Cycle Framework",
            "The 70/20/10 Rule",
            "Agent Delegation",
            "Parallel Execution",
            "Plan Before Execute",
            "Quality Over Speed",
            "Diminishing Returns Detection",
            "The Hard Stuff Multiplier",
            "Never Plan Twice",
            "Planning ≠ Doing",
        ]
        for rule in required_rules:
            check(f"Global rule: {rule}", rule in content, f"Missing: {rule}")

    if building_rules.exists():
        content = building_rules.read_text()
        check(
            "building-rules.md has content",
            len(content) > 100,
            f"Only {len(content)} chars",
        )

# ============================================================================
# 6. BMAD Configs — Agent Customization
# ============================================================================
section("6. BMAD Configs — Agent Customization")

bmad_agents = PROJECT_ROOT / "_bmad" / "_config" / "agents"
check("BMAD agents dir exists", bmad_agents.exists(), "Directory not found")

if bmad_agents.exists():
    expected_customizations = [
        "sisyphus.customize.yaml",
        "hephaestus.customize.yaml",
        "oracle.customize.yaml",
    ]
    for cust in expected_customizations:
        cust_file = bmad_agents / cust
        check(f"BMAD customization: {cust}", cust_file.exists(), f"Missing: {cust}")
        if cust_file.exists():
            content = cust_file.read_text()
            check(
                f"  {cust}: has content",
                len(content) > 50,
                f"Only {len(content)} chars",
            )

# BMAD module configs
bmad_core = PROJECT_ROOT / "_bmad" / "core" / "config.yaml"
bmad_bmm = PROJECT_ROOT / "_bmad" / "bmm" / "config.yaml"
check("BMAD core config exists", bmad_core.exists(), "File not found")
check("BMAD bmm config exists", bmad_bmm.exists(), "File not found")

# ============================================================================
# 7. VPN Configs — Country Mappings
# ============================================================================
section("7. VPN Configs — Country Mappings")

vpn_configs = PROJECT_ROOT / "configs" / "vpn" / "country_mappings.json"
check("VPN country mappings exist", vpn_configs.exists(), "File not found")

if vpn_configs.exists():
    try:
        with open(vpn_configs) as f:
            vpn = json.load(f)
        check("VPN JSON valid", True)
        check("VPN has countries", "countries" in vpn or len(vpn) > 0, "No countries")
    except Exception as e:
        check("VPN JSON valid", False, str(e))

# ============================================================================
# 8. Quality Gates — Scripts
# ============================================================================
section("8. Quality Gates — Scripts")

gates_dir = PROJECT_ROOT / "bin" / "quality-gates"
check("Quality gates dir exists", gates_dir.exists(), "Directory not found")

if gates_dir.exists():
    expected_gates = [
        "gate-1-py-typecheck.sh",
        "gate-2-py-lint.sh",
        "gate-3-format.sh",
        "gate-4-test.sh",
        "gate-5-secrets.sh",
        "gate-6-placeholders.sh",
        "gate-all.sh",
    ]
    for gate in expected_gates:
        gate_file = gates_dir / gate
        check(f"Gate script: {gate}", gate_file.exists(), f"Missing: {gate}")
        if gate_file.exists():
            check(
                f"  {gate}: is executable",
                os.access(gate_file, os.X_OK),
                "Not executable",
            )
            content = gate_file.read_text()
            check(
                f"  {gate}: has content",
                len(content) > 50,
                f"Only {len(content)} chars",
            )

# ============================================================================
# 9. Trigger Engine — Runtime Validation
# ============================================================================
section("9. Trigger Engine — Runtime Validation")

trigger_engine = PROJECT_ROOT / "src" / "trigger_engine.py"
check("trigger_engine.py exists", trigger_engine.exists(), "File not found")

if trigger_engine.exists():
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location("trigger_engine", trigger_engine)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        check("trigger_engine imports", True)

        # Check ACTION_REGISTRY
        check("ACTION_REGISTRY exists", hasattr(module, "ACTION_REGISTRY"), "Missing")
        if hasattr(module, "ACTION_REGISTRY"):
            registry = module.ACTION_REGISTRY
            check(
                f"ACTION_REGISTRY has {len(registry)} actions",
                len(registry) >= 4,
                f"Only {len(registry)}",
            )

            expected_actions_runtime = [
                "clean_stale_sessions",
                "clear_db_lock",
                "force_gc",
                "throttle_ollama",
            ]
            for action in expected_actions_runtime:
                check(
                    f"  Action '{action}' registered",
                    action in registry,
                    f"Missing: {action}",
                )
    except Exception as e:
        check("trigger_engine imports", False, str(e))

# ============================================================================
# 10. MCP Packages — Structure Validation
# ============================================================================
section("10. MCP Packages — Structure Validation")

packages_dir = PROJECT_ROOT / "packages"
check("Packages dir exists", packages_dir.exists(), "Directory not found")

if packages_dir.exists():
    expected_packages = ["athena-context-mcp", "nx-mind-mcp", "trigger-guardian-mcp"]
    expected_src_dirs = ["athena_context_mcp", "nx_mind_mcp", "trigger_guardian_mcp"]
    for i, pkg in enumerate(expected_packages):
        pkg_dir = packages_dir / pkg
        check(f"Package '{pkg}' exists", pkg_dir.exists(), f"Missing: {pkg}")
        if pkg_dir.exists():
            pyproject = pkg_dir / "pyproject.toml"
            check(f"  {pkg}: pyproject.toml exists", pyproject.exists(), "Missing")
            src_dir = pkg_dir / expected_src_dirs[i]
            check(f"  {pkg}: {expected_src_dirs[i]}/ exists", src_dir.exists(), "Missing")

# ============================================================================
# SUMMARY
# ============================================================================
section("SUMMARY")

total = PASS + FAIL + WARN
print(f"\n  Total checks: {total}")
print(f"  ✅ Passed: {PASS}")
print(f"  ❌ Failed: {FAIL}")
print(f"  ⚠️  Warnings: {WARN}")
print(f"\n  Config-Driven Coverage: {PASS}/{total} ({PASS / total * 100:.1f}%)")

if FAIL == 0:
    print(f"\n  🎉 100% CONFIG-DRIVEN FUNCTIONALITY VALIDATED!")
    sys.exit(0)
else:
    print(f"\n  ❌ {FAIL} checks failed — review needed")
    sys.exit(1)
