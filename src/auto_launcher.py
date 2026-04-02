"""Auto Launcher — Detect app and auto-start services"""

import logging, subprocess, time
from typing import Dict, List

logger = logging.getLogger(__name__)


class AutoLauncher:
    def __init__(self):
        self._watchers: Dict[str, dict] = {}

    def watch(self, app_name: str, service_cmd: str, check_interval: int = 5):
        self._watchers[app_name] = {
            "cmd": service_cmd,
            "interval": check_interval,
            "last_check": 0,
            "running": False,
        }

    def check(self) -> Dict[str, bool]:
        import psutil

        results = {}
        for app_name, config in self._watchers.items():
            now = time.time()
            if now - config["last_check"] < config["interval"]:
                results[app_name] = config["running"]
                continue
            config["last_check"] = now
            is_running = any(
                app_name.lower() in p.name().lower() for p in psutil.process_iter(["name"])
            )
            if is_running and not config["running"]:
                try:
                    subprocess.Popen(config["cmd"], shell=True)
                    config["running"] = True
                    logger.info(f"AutoLauncher: Started service for {app_name}")
                except Exception as e:
                    logger.error(f"AutoLauncher: Failed to start: {e}")
            elif not is_running and config["running"]:
                config["running"] = False
            results[app_name] = config["running"]
        return results
