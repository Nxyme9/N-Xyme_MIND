#!/usr/bin/env python3
"""
athena.boot.orchestrator
=========================
Modular boot sequence orchestrator.
Replaces the monolithic .agent/scripts/boot.py
"""

import sys
from datetime import datetime
from athena.boot.constants import (
    PROJECT_ROOT,
    RED,
    GREEN,
    YELLOW,
    CYAN,
    BOLD,
    DIM,
    RESET,
)


def main():
    # Lazy Imports for Speed
    from athena.boot.loaders.ui import UILoader
    from athena.boot.loaders.state import StateLoader
    from athena.boot.loaders.identity import IdentityLoader
    from athena.boot.loaders.memory import MemoryLoader
    from athena.boot.loaders.system import SystemLoader
    from athena.boot.loaders.prefetch import PrefetchLoader
    from athena.boot.loaders.token_budget import (
        measure_boot_files,
        display_gauge,
        auto_compact_if_needed,
    )

    # Phase 0: Check for --verify flag
    if len(sys.argv) > 1 and sys.argv[1] == "--verify":
        # We can implement a verify mode here later if needed
        # For now, just pass
        pass

    # Phase 1: Watchdog & Pre-flight (minimal sequential gate)
    StateLoader.enable_watchdog()
    UILoader.divider("⚡ ATHENA BOOT SEQUENCE")

    # Daemon check — fast (pgrep), must run before pool
    SystemLoader.enforce_daemon()

    # Identity integrity — fast (SHA-384 of one file), hard gate
    if not IdentityLoader.verify_semantic_prime():
        return 1

    # Security patch — instant, non-blocking
    try:
        from athena.core.security import patch_dspy_cache_security

        patch_dspy_cache_security()
        print(f"   🛡️  Security: DiskCache mitigation active.")
    except ImportError:
        pass
    except Exception as e:
        print(f"   ⚠️  Security Patch Failed: {e}")

    StateLoader.check_prior_crashes()
    StateLoader.check_canary_overdue()

    # Boot timestamp — instant
    try:
        last_boot_log = PROJECT_ROOT / ".agent" / "state" / "last_boot.log"
        last_boot_log.parent.mkdir(parents=True, exist_ok=True)
        with open(last_boot_log, "w") as f:
            f.write(datetime.now().isoformat())
    except Exception as e:
        print(f"   ⚠️  Boot Log Update Fail: {e}")

    # Phase 2: Session Creation (fast — file write)
    session_id = MemoryLoader.create_session()

    # Phase 2.1: Record session start reference (for passive observation)
    try:
        from athena.auditors.audit_observations import record_start_ref

        record_start_ref()
    except Exception:
        pass  # Non-critical — observations are optional

    # Phase 3: Audit (Reset) — instant
    try:
        sys.path.insert(0, str(PROJECT_ROOT / ".agent" / "scripts"))
        from semantic_audit import reset_audit

        reset_audit()
    except Exception:
        pass

    # Phase 4: Parallel Background Work (ALL non-gating work moved here)
    from concurrent.futures import ThreadPoolExecutor
    from athena.core.health import HealthCheck
    from athena.boot.loaders.context_summaries import (
        generate_summaries,
        display_summary_status,
    )

    def run_health_check_wrapper():
        try:
            if not HealthCheck.run_all():
                print(
                    f"{RED}⚠️  System health check failed. Proceeding with caution...{RESET}"
                )
        except Exception:
            pass

    # Shared state for parallel results
    context_summaries = {}
    token_counts = {}
    last_session = ""

    def run_context_summaries():
        nonlocal context_summaries
        context_summaries = generate_summaries()

    def run_recall_and_budget():
        nonlocal last_session, token_counts
        last_session = MemoryLoader.recall_last_session()
        token_counts = measure_boot_files()
        token_counts = auto_compact_if_needed(token_counts)

    with ThreadPoolExecutor(max_workers=8) as executor:
        # Fast operations
        executor.submit(MemoryLoader.capture_context)
        executor.submit(IdentityLoader.inject_auto_protocols, "startup session boot")
        executor.submit(run_context_summaries)
        executor.submit(PrefetchLoader.prefetch_hot_files)

        # Previously-sequential operations (now background)
        executor.submit(run_recall_and_budget)
        executor.submit(SystemLoader.verify_environment)  # Was blocking Phase 1
        executor.submit(SystemLoader.sync_ui)  # Was in Phase 1.5

        # Expensive but non-blocking
        executor.submit(MemoryLoader.prime_semantic)  # 10s timeout (was 60s)
        executor.submit(run_health_check_wrapper)

        # REMOVED: prewarm_search_cache — negligible benefit, 15-45s cost

    # Display sync items (all data ready from parallel phase)
    MemoryLoader.display_learnings_snapshot()
    IdentityLoader.display_cognitive_profile()
    IdentityLoader.display_cos_status()
    display_summary_status(context_summaries)

    # Phase 8: Sidecar Launch (Sovereign Index)
    try:
        import subprocess

        sidecar_path = PROJECT_ROOT / ".agent" / "scripts" / "sidecar.py"
        subprocess.Popen(
            [sys.executable, str(sidecar_path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        print("   🛡️  Sidecar Launched (PID: Independent)")
    except Exception as e:
        print(f"   ⚠️  Sidecar Fail: {e}")

    # Disable watchdog
    StateLoader.disable_watchdog()

    # Final Summary
    print(f"\n{BOLD}{'─' * 60}{RESET}")
    print(f"{GREEN}{BOLD}⚡ Ready.{RESET} Session: {session_id}")
    print(
        f"{DIM}⚖️  Law #6 Reminder: Run 'python3 .agent/scripts/quicksave.py \"...\"' after completing work.{RESET}"
    )
    print(f"{BOLD}{'─' * 60}{RESET}\n")

    # Display Token Budget Gauge
    display_gauge(token_counts)

    return 0


if __name__ == "__main__":
    sys.exit(main())
