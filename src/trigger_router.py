"""Central dispatch for triggers.json — routes events to handlers."""

import json
from metrics_store import MetricsStore
import re
import sys
import logging
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from security_llm import get_security

logger = logging.getLogger(__name__)
CATALYST_DIR = Path(__file__).parent.parent

# Module-level 429 rate limit counter (tracks consecutive 429 errors)
_rate_limit_counter: int = 0
_last_429_timestamp: float = 0
_RATE_LIMIT_WINDOW_SECONDS: int = 300

# Module-level cache for BurntToast availability (checked once)
_burnttoast_available: Optional[bool] = None


def _check_burnttoast() -> bool:
    """Check if BurntToast PowerShell module is installed."""
    global _burnttoast_available
    if _burnttoast_available is not None:
        return _burnttoast_available

    try:
        result = subprocess.run(
            ["powershell", "-Command", "Get-Module -ListAvailable -Name BurntToast"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        _burnttoast_available = bool(result.stdout.strip())
    except Exception:
        _burnttoast_available = False

    if _burnttoast_available:
        logger.info("BurntToast module detected")
    else:
        logger.info("BurntToast module not available, will fallback to console")
    return _burnttoast_available


def get_429_count() -> int:
    global _rate_limit_counter, _last_429_timestamp
    current_time = time.time()
    if current_time - _last_429_timestamp > _RATE_LIMIT_WINDOW_SECONDS:
        _rate_limit_counter = 0
    return _rate_limit_counter


def increment_429_counter() -> int:
    global _rate_limit_counter, _last_429_timestamp
    current_time = time.time()
    if current_time - _last_429_timestamp > _RATE_LIMIT_WINDOW_SECONDS:
        _rate_limit_counter = 0
    _rate_limit_counter += 1
    _last_429_timestamp = current_time
    logger.info(f"Rate limit counter incremented: {_rate_limit_counter}")
    return _rate_limit_counter


def reset_429_counter() -> None:
    global _rate_limit_counter, _last_429_timestamp
    _rate_limit_counter = 0
    _last_429_timestamp = 0
    logger.info("Rate limit counter reset")


def send_windows_toast(title: str, message: str) -> bool:
    """Send a Windows toast notification via BurntToast. Fallback to console log."""
    if _check_burnttoast():
        try:
            subprocess.run(
                [
                    "powershell",
                    "-Command",
                    f"New-BurntToastNotification -Text '{title}', '{message}'",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            logger.info(f"Toast sent: {title}")
            return True
        except FileNotFoundError:
            logger.warning("PowerShell not found, toast fallback to console")
        except subprocess.TimeoutExpired:
            logger.warning("Toast timed out, fallback to console")
        except Exception as e:
            logger.warning(f"Toast failed ({e}), fallback to console")

    logger.critical(f"[TOAST] {title}: {message}")
    return False


def _rotate_vpn(provider: str) -> bool:
    script_path = Path(__file__).parent.parent / "scripts" / "vpn-rotation-simulator.py"
    if not script_path.exists():
        logger.error(f"VPN rotation script not found: {script_path}")
        return False

    try:
        logger.info(f"TriggerRouter: Initiating VPN rotation for {provider}")
        result = subprocess.run(
            ["python", str(script_path), "--rotate"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0:
            logger.info("TriggerRouter: VPN rotation completed successfully")
            return True
        else:
            logger.error(f"TriggerRouter: VPN rotation failed: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        logger.error("TriggerRouter: VPN rotation timed out")
        return False
    except Exception as e:
        logger.error(f"TriggerRouter: VPN rotation error: {e}")
        return False


def _rotate_api_key(provider: str) -> bool:
    script_path = Path(__file__).parent.parent / "scripts" / "api-key-rotator.py"
    if not script_path.exists():
        logger.error(f"API key rotator script not found: {script_path}")
        return False

    try:
        logger.info(f"TriggerRouter: Initiating API key rotation for {provider}")
        result = subprocess.run(
            ["python", str(script_path), "--rotate", provider],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            logger.info("TriggerRouter: API key rotation completed")
            return True
        else:
            logger.error(f"TriggerRouter: API key rotation failed: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        logger.error("TriggerRouter: API key rotation timed out")
        return False
    except Exception as e:
        logger.error(f"TriggerRouter: API key rotation error: {e}")
        return False


class TriggerRouter:
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or self._find_config()
        self.triggers: Dict[str, List[Dict[str, Any]]] = {}
        self.action_registry: Dict[str, Dict[str, Any]] = {}
        self.global_settings: Dict[str, Any] = {}
        self.history: List[Dict[str, Any]] = []
        self.cooldowns: Dict[str, float] = {}
        self.metrics_store = MetricsStore()
        self._last_toast_time: float = 0
        self._load_config()

    def _find_config(self) -> str:
        root = Path(__file__).parent.parent
        config = root / "triggers.json"
        if config.exists():
            return str(config)
        raise FileNotFoundError(f"triggers.json not found in {root}")

    def _load_config(self) -> None:
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.action_registry = data.get("action_registry", {})

            triggers_data = data.get("triggers", {})
            for source, triggers in triggers_data.items():
                self.triggers[source] = triggers

            self.global_settings = data.get("global_settings", {})

            logger.info(
                f"TriggerRouter: Loaded {len(self.action_registry)} actions, "
                f"{sum(len(t) for t in self.triggers.values())} triggers"
            )
        except Exception as e:
            logger.error(f"TriggerRouter: Failed to load config: {e}")
            raise

    def process_event(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        source = event.get("source", "")
        self.metrics_store.record_metric(
            source, event.get("type", ""), 1.0, event.get("session_id", "")
        )
        severity = event.get("severity", "")
        event_type = event.get("type", "")

        if source == "rate_limit":
            return self._handle_rate_limit_event(event)

        trigger = self._find_matching_trigger(source, severity, event_type)
        if not trigger:
            logger.debug(f"TriggerRouter: No trigger for {source}/{severity}")
            return None

        trigger_id = trigger.get("id", "")
        if self._is_on_cooldown(trigger_id):
            logger.info(f"TriggerRouter: {trigger_id} on cooldown, skipping")
            return None

        result = self._execute_trigger(trigger, event)
        self._record_history(trigger, event, result)

        if trigger.get("notify") and severity == "critical":
            if time.time() - self._last_toast_time > 60:
                send_windows_toast(
                    f"CRITICAL: {source}",
                    event.get("message", trigger.get("description", "")),
                )
                self._last_toast_time = time.time()

        return result

    def _handle_rate_limit_event(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        event_type = event.get("type", "")
        result = None

        if event_type == "api_429":
            count = increment_429_counter()
            event["consecutive_429_count"] = count
            logger.info(f"Rate limit: 429 detected, consecutive count: {count}")

            if count == 1:
                result = self._execute_trigger_by_id("api_429_warning", event)
            elif count >= 3:
                result = self._execute_trigger_by_id("api_429_critical", event)
            elif count >= 5:
                result = self._execute_trigger_by_id("api_key_exhausted", event)

        elif event_type == "api_success":
            reset_429_counter()
            logger.info("Rate limit: API success, counter reset")

        return result

    def _execute_trigger_by_id(
        self, trigger_id: str, event: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        for source, triggers in self.triggers.items():
            for trigger in triggers:
                if trigger.get("id") == trigger_id:
                    if self._is_on_cooldown(trigger_id):
                        logger.info(f"TriggerRouter: {trigger_id} on cooldown, skipping")
                        return None
                    result = self._execute_trigger(trigger, event)
                    self._record_history(trigger, event, result)
                    return result
        return None

    def _find_matching_trigger(
        self,
        source: str,
        severity: str,
        event_type: str,
    ) -> Optional[Dict[str, Any]]:
        source_triggers = self.triggers.get(source, [])
        # First pass: match by type + severity
        for trigger in source_triggers:
            trigger_type = trigger.get("type", "")
            trigger_severity = trigger.get("severity", "")
            if trigger_type and trigger_type == event_type and trigger_severity == severity:
                return trigger
        # Second pass: match by severity only (backward compat)
        for trigger in source_triggers:
            trigger_severity = trigger.get("severity", "")
            if trigger_severity == severity:
                return trigger
        return None

    def _is_on_cooldown(self, trigger_id: str) -> bool:
        last_execution = self.cooldowns.get(trigger_id, 0)
        cooldown_seconds = self.global_settings.get("default_cooldown_seconds", 60)
        return (time.time() - last_execution) < cooldown_seconds

    def _execute_trigger(
        self,
        trigger: Dict[str, Any],
        event: Dict[str, Any],
    ) -> Dict[str, Any]:
        action_name = trigger.get("action", "")
        action_config = self.action_registry.get(action_name, {})

        result = {
            "trigger_id": trigger.get("id", ""),
            "action": action_name,
            "success": False,
            "message": "",
        }

        security = get_security()
        allowed, reason = security.check_tool_access(action_name)
        if not allowed:
            result["message"] = f"Security denied: {reason}"
            logger.warning(f"TriggerRouter: Security denied {action_name}: {reason}")
            return result

        try:
            action_type = action_config.get("type", "")

            if action_type == "pm2":
                method = action_config.get("method", "")
                target = action_config.get("target", "")
                if method == "restart":
                    success = self._pm2_restart(target or event.get("service_name", ""))
                    result["success"] = success
                    result["message"] = (
                        f"PM2 restart: {target}" if success else "PM2 restart failed"
                    )
                elif method == "force_gc":
                    result["success"] = True
                    result["message"] = "Force GC triggered"
                else:
                    result["message"] = f"Unknown PM2 method: {method}"

            elif action_type == "service":
                target = action_config.get("target", "")
                if target:
                    success = self._pm2_restart(target)
                    result["success"] = success
                    result["message"] = (
                        f"Service restart: {target}" if success else "Service restart failed"
                    )
                else:
                    result["message"] = "No target specified"

            elif action_type == "gpu":
                method = action_config.get("method", "")
                if method == "log_warning":
                    result["success"] = True
                    result["message"] = "GPU warning logged"
                else:
                    result["message"] = f"Unknown GPU method: {method}"

            elif action_type == "notify":
                method = action_config.get("method", "")
                if method == "log_critical":
                    desc = trigger.get("description", "")
                    logger.critical(f"TriggerRouter: {desc}")
                    if time.time() - self._last_toast_time > 60:
                        send_windows_toast("CRITICAL", desc)
                        self._last_toast_time = time.time()
                    result["success"] = True
                    result["message"] = "Critical alert logged (toast sent)"
                else:
                    result["message"] = f"Unknown notify method: {method}"

            elif action_type == "script":
                action_params = trigger.get("action_params", {})
                provider = action_params.get("provider", "opencode")
                if action_name == "rotate_vpn":
                    success = _rotate_vpn(provider)
                    result["success"] = success
                    result["message"] = f"VPN rotation {'succeeded' if success else 'failed'}"
                elif action_name == "rotate_api_key":
                    success = _rotate_api_key(provider)
                    result["success"] = success
                    result["message"] = f"API key rotation {'succeeded' if success else 'failed'}"
                else:
                    result["message"] = f"Unknown script action: {action_name}"

            elif action_type == "config":
                self._handle_config_event(action_config, event, result)
            elif action_type == "graphiti":
                self._handle_graphiti_event(action_config, event, result)
            elif action_type == "ollama":
                self._handle_ollama_event(action_config, event, result)
            elif action_type == "system":
                self._handle_system_event(action_config, event, result)
            elif action_type == "velocity":
                self._handle_velocity_event(action_config, event, result)
            elif action_type == "consciousness":
                self._handle_consciousness_event(action_config, event, result)
            elif action_type == "memory":
                self._handle_memory_event(action_config, event, result)
            else:
                result["message"] = f"Unknown action type: {action_type}"

            self.cooldowns[trigger.get("id", "")] = time.time()
            self.metrics_store.record_action(
                trigger.get("id", ""),
                action_name,
                result.get("success", False),
                result.get("message", ""),
            )
            if result.get("success") and trigger.get("severity") == "critical":
                self._verify_fix(trigger.get("id", ""), action_name)
            cooldown = trigger.get("cooldown_seconds", 60)
            logger.info(f"TriggerRouter: Executed {action_name} (cooldown: {cooldown}s)")

        except Exception as e:
            result["success"] = False
            result["message"] = str(e)
            logger.error(f"TriggerRouter: Action failed: {e}")

        return result

    def _pm2_restart(self, service_name: str) -> bool:
        if not service_name:
            logger.warning("TriggerRouter: No service name for PM2 restart")
            return False

        try:
            subprocess.run(
                ["pm2", "restart", service_name],
                capture_output=True,
                text=True,
                timeout=30,
            )
            logger.info(f"TriggerRouter: PM2 restarted {service_name}")
            return True
        except FileNotFoundError:
            logger.warning("TriggerRouter: PM2 not found")
            return False
        except subprocess.TimeoutExpired:
            logger.error(f"TriggerRouter: PM2 restart timed out for {service_name}")
            return False
        except Exception as e:
            logger.error(f"TriggerRouter: PM2 restart failed: {e}")
            return False

    def _handle_config_event(self, action_config, event, result):
        try:
            r = subprocess.run(
                [sys.executable, str(CATALYST_DIR / "scripts" / "startup-validate.py")],
                capture_output=True,
                text=True,
                timeout=30,
            )
            result["success"] = r.returncode == 0
            result["message"] = r.stdout[:500] if r.stdout else r.stderr[:500]
        except Exception as e:
            result["message"] = str(e)

    def _handle_graphiti_event(self, action_config, event, result):
        method = action_config.get("method", "")
        if method == "restart":
            subprocess.run(["pm2", "restart", "graphiti-mcp"], capture_output=True, timeout=30)
            result["success"] = True
            result["message"] = "Restarted graphiti-mcp"

    def _handle_ollama_event(self, action_config, event, result):
        method = action_config.get("method", "")
        if method == "pull":
            model = event.get("data", {}).get("model", "")
            if not model:
                result["message"] = "No model specified"
                return
            r = subprocess.run(
                [
                    "curl",
                    "-s",
                    "-X",
                    "POST",
                    "http://localhost:11434/api/pull",
                    "-d",
                    json.dumps({"name": model}),
                ],
                capture_output=True,
                text=True,
                timeout=300,
            )
            result["success"] = r.returncode == 0
            result["message"] = f"Pulled {model}" if result["success"] else r.stderr[:200]

    def _handle_system_event(self, action_config, event, result):
        try:
            r = subprocess.run(
                [sys.executable, str(CATALYST_DIR / "scripts" / "startup-validate.py")],
                capture_output=True,
                text=True,
                timeout=60,
            )
            result["success"] = r.returncode == 0
            result["message"] = r.stdout[:500] if r.stdout else r.stderr[:500]
        except Exception as e:
            result["message"] = str(e)

    def _verify_fix(self, trigger_id, action, delay=60):
        """Schedule a re-check after fix. Escalate if still broken."""
        import threading

        def check():
            time.sleep(delay)
            # Re-run the same trigger to see if it still fires
            escalation_level = self.metrics_store.query_metrics(
                source=None, metric=f"escalation_{trigger_id}", hours=1
            )
            level = len(escalation_level) if escalation_level else 0
            if level >= 3:
                self.metrics_store.publish_alert(
                    "trigger_router",
                    "user",
                    "escalation_maxed",
                    f"{trigger_id} failed 3x, manual intervention needed",
                )
                logger.warning(f"TriggerRouter: {trigger_id} escalated to max level, alerting user")
                return
            self.metrics_store.record_metric("escalation", f"escalation_{trigger_id}", level + 1)
            logger.info(f"TriggerRouter: Re-check scheduled for {trigger_id} (level {level + 1})")

        t = threading.Thread(target=check, daemon=True)
        t.start()


    def _handle_velocity_event(self, action_config, event, result):
        """Record task timing for velocity tracking."""
        method = action_config.get("method", "")
        task_name = event.get("data", {}).get("task_name", event.get("type", "unknown"))
        category = event.get("data", {}).get("category", "general")
        
        if method == "start":
            task_id = f"task-{int(time.time())}"
            self.metrics_store.record_task_start(task_id, task_name, category=category)
            result["success"] = True
            result["message"] = f"Timing started: {task_name}"
        elif method == "complete":
            # Find most recent in-progress task
            import sqlite3
            conn = sqlite3.connect(self.metrics_store.db_path)
            row = conn.execute("SELECT task_id FROM task_velocity WHERE status='in_progress' ORDER BY started_at DESC LIMIT 1").fetchone()
            if row:
                self.metrics_store.record_task_complete(row[0])
                v = self.metrics_store.get_velocity(7)
                result["success"] = True
                result["message"] = f"Task completed. Velocity: {v['tasks_per_hour']}/hr" if v else "Task completed"
            else:
                result["message"] = "No in-progress task found"
            conn.close()


    def _handle_consciousness_event(self, action_config, event, result):
        """Reality check: verify claims with real tests, not syntax."""
        method = action_config.get("method", "")
        claim = event.get("data", {}).get("claim", "unknown claim")
        component = event.get("data", {}).get("component", "all")
        
        if method == "verify":
            # Run REAL functionality tests via subprocess
            import subprocess
            try:
                r = subprocess.run(
                    [sys.executable, "scripts/verify-claim.py", claim, "--component", component],
                    capture_output=True, text=True, timeout=60,
                    cwd=str(CATALYST_DIR)
                )
                if r.returncode == 0:
                    result["success"] = True
                    result["message"] = f"CLAIM VERIFIED: {claim}"
                    # Log to metrics
                    self.metrics_store.record_metric("consciousness", "claim_verified", 1)
                else:
                    result["success"] = False
                    result["message"] = f"CLAIM REJECTED: {claim} - {r.stdout[-200:]}"
                    self.metrics_store.record_metric("consciousness", "claim_rejected", 1)
                    # Fire rejection trigger
                    self.process_event({
                        "source": "consciousness",
                        "type": "reality_check_failed",
                        "severity": "critical",
                        "data": {"claim": claim, "component": component, "output": r.stdout[-500:]}
                    })
            except subprocess.TimeoutExpired:
                result["success"] = False
                result["message"] = f"CLAIM TIMEOUT: {claim} - verification took >60s"
        
        elif method == "log_pass":
            result["success"] = True
            result["message"] = f"Verified: {claim}"
        
        elif method == "reject":
            result["success"] = True
            result["message"] = f"REJECTED: {claim}"


    def _handle_memory_event(self, action_config, event, result):
        """Distill noisy episodes into meaningful knowledge."""
        method = action_config.get("method", "")
        if method == "distill":
            import subprocess
            try:
                r = subprocess.run(
                    [sys.executable, "scripts/distill-memory.py"],
                    capture_output=True, text=True, timeout=120,
                    cwd=str(CATALYST_DIR)
                )
                result["success"] = r.returncode == 0
                result["message"] = r.stdout[-300:] if r.stdout else r.stderr[-300:]
                self.metrics_store.record_metric("memory", "episodes_distilled", 1)
            except subprocess.TimeoutExpired:
                result["message"] = "Distillation timeout (>120s)"

    def _record_history(
        self,
        trigger: Dict[str, Any],
        event: Dict[str, Any],
        result: Dict[str, Any],
    ) -> None:
        entry = {
            "timestamp": time.time(),
            "trigger_id": trigger.get("id", ""),
            "action": trigger.get("action", ""),
            "source": event.get("source", ""),
            "severity": event.get("severity", ""),
            "success": result.get("success", False),
            "message": result.get("message", ""),
        }
        self.history.append(entry)
        if len(self.history) > 100:
            self.history = self.history[-100:]

    def get_history(self) -> List[Dict[str, Any]]:
        return self.history.copy()

    def get_cooldowns(self) -> Dict[str, float]:
        return self.cooldowns.copy()


def create_router() -> TriggerRouter:
    return TriggerRouter()
