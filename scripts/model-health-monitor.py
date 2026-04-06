#!/usr/bin/env python3
"""Model Health Monitor - Daemon that monitors local (Ollama) and cloud model availability, latency, and VRAM usage."""

import sys
import json
import time
import logging
import argparse
import subprocess
from pathlib import Path
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional, Dict, Any, List

# Try to import requests, fall back to urllib if not available
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    import urllib.request
    import urllib.error

logger = logging.getLogger("model-health-monitor")


class ModelHealthStatus(Enum):
    """Health status of a model."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ModelHealth:
    """Health information for a model."""
    model_name: str
    provider: str
    status: ModelHealthStatus = ModelHealthStatus.UNKNOWN
    latency_ms: float = 0.0
    last_check: float = 0.0
    consecutive_failures: int = 0
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "model_name": self.model_name,
            "provider": self.provider,
            "status": self.status.value,
            "latency_ms": self.latency_ms,
            "last_check": self.last_check,
            "consecutive_failures": self.consecutive_failures,
            "error": self.error
        }


@dataclass
class VRAMInfo:
    """VRAM usage information."""
    total_gb: float = 0.0
    used_gb: float = 0.0
    free_gb: float = 0.0
    gpu_name: str = "unknown"
    temperature_c: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "total_gb": self.total_gb,
            "used_gb": self.used_gb,
            "free_gb": self.free_gb,
            "gpu_name": self.gpu_name,
            "temperature_c": self.temperature_c
        }


class HealthMonitor:
    """Monitors model health, VRAM usage, and provides health reports."""

    def __init__(self, config_path: str = "configs/model_router.json", state_file: str = ".sisyphus/model_health.json"):
        self.config_path = Path(config_path)
        self.state_file = Path(state_file)
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        
        self.config = self._load_config()
        self.models: Dict[str, ModelHealth] = {}
        self.ollama_available: bool = False
        self.vram_info: VRAMInfo = VRAMInfo()
        
        self._load_state()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from model_router.json"""
        if self.config_path.exists():
            try:
                with open(self.config_path) as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading config: {e}")
        
        # Return default config
        return {
            "health_check": {
                "interval_seconds": 30,
                "timeout_seconds": 5,
                "consecutive_failures_threshold": 3
            },
            "models": {
                "local": {
                    "ollama/qwen2.5-coder:7b": {"provider": "ollama", "endpoint": "http://localhost:11434"},
                    "ollama/llama3.2:3b": {"provider": "ollama", "endpoint": "http://localhost:11434"}
                }
            }
        }

    def _load_state(self):
        """Load previous state from file"""
        if self.state_file.exists():
            try:
                with open(self.state_file) as f:
                    data = json.load(f)
                
                # Load model states
                for model_name, model_data in data.get("models", {}).items():
                    self.models[model_name] = ModelHealth(
                        model_name=model_data.get("model_name", model_name),
                        provider=model_data.get("provider", "unknown"),
                        status=ModelHealthStatus(model_data.get("status", "unknown")),
                        latency_ms=model_data.get("latency_ms", 0.0),
                        last_check=model_data.get("last_check", 0.0),
                        consecutive_failures=model_data.get("consecutive_failures", 0),
                        error=model_data.get("error")
                    )
                
                # Load VRAM info
                vram_data = data.get("vram", {})
                self.vram_info = VRAMInfo(
                    total_gb=vram_data.get("total_gb", 0.0),
                    used_gb=vram_data.get("used_gb", 0.0),
                    free_gb=vram_data.get("free_gb", 0.0),
                    gpu_name=vram_data.get("gpu_name", "unknown"),
                    temperature_c=vram_data.get("temperature_c", 0)
                )
                
                self.ollama_available = data.get("ollama_available", False)
                
                logger.info(f"Loaded state with {len(self.models)} model states")
            except Exception as e:
                logger.error(f"Error loading state: {e}")

    def save_state(self) -> None:
        """Save current state to file"""
        data = {
            "timestamp": time.time(),
            "ollama_available": self.ollama_available,
            "vram": self.vram_info.to_dict(),
            "models": {
                name: model.to_dict()
                for name, model in self.models.items()
            }
        }
        
        try:
            with open(self.state_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.debug(f"State saved to {self.state_file}")
        except Exception as e:
            logger.error(f"Error saving state: {e}")

    def load_state(self) -> None:
        """Load previous state (alias for compatibility)"""
        self._load_state()

    def check_ollama(self) -> bool:
        """Check if Ollama is running via /api/tags"""
        timeout = self.config.get("health_check", {}).get("timeout_seconds", 5)
        endpoint = self.config.get("health_check", {}).get("checks", {}).get("ollama", {}).get("endpoint")
        
        if not endpoint:
            endpoint = "http://localhost:11434/api/tags"
        
        logger.debug(f"Checking Ollama at {endpoint}")
        
        try:
            if HAS_REQUESTS:
                response = requests.get(endpoint, timeout=timeout)
                self.ollama_available = response.status_code == 200
            else:
                req = urllib.request.Request(endpoint)
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    self.ollama_available = resp.status == 200
            
            logger.info(f"Ollama health check: {'available' if self.ollama_available else 'unavailable'}")
            return self.ollama_available
        except Exception as e:
            logger.warning(f"Ollama health check failed: {e}")
            self.ollama_available = False
            return False

    def check_model(self, model_name: str, provider: str) -> ModelHealth:
        """Check individual model availability by sending a minimal prompt"""
        timeout = self.config.get("health_check", {}).get("timeout_seconds", 5)
        
        health = ModelHealth(
            model_name=model_name,
            provider=provider,
            last_check=time.time()
        )
        
        if provider != "ollama":
            # For non-ollama providers, assume healthy (cloud models)
            health.status = ModelHealthStatus.HEALTHY
            health.latency_ms = 0.0
            return health
        
        # Check Ollama model with a simple generate request
        endpoint = "http://localhost:11434/api/generate"
        
        try:
            start_time = time.time()
            
            payload = {
                "model": model_name.split("/")[-1] if "/" in model_name else model_name,
                "prompt": "Hi",
                "options": {"num_predict": 1}
            }
            
            if HAS_REQUESTS:
                response = requests.post(endpoint, json=payload, timeout=timeout)
                latency = (time.time() - start_time) * 1000
                
                if response.status_code == 200:
                    health.status = ModelHealthStatus.HEALTHY
                    health.latency_ms = latency
                    health.consecutive_failures = 0
                else:
                    health.status = ModelHealthStatus.UNHEALTHY
                    health.error = f"HTTP {response.status_code}"
                    health.consecutive_failures = 1
            else:
                data = json.dumps(payload).encode("utf-8")
                req = urllib.request.Request(endpoint, data=data, headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    latency = (time.time() - start_time) * 1000
                    if resp.status == 200:
                        health.status = ModelHealthStatus.HEALTHY
                        health.latency_ms = latency
                        health.consecutive_failures = 0
                    else:
                        health.status = ModelHealthStatus.UNHEALTHY
                        health.error = f"HTTP {resp.status}"
                        health.consecutive_failures = 1
            
            logger.debug(f"Model {model_name}: status={health.status.value}, latency={health.latency_ms:.0f}ms")
            
        except Exception as e:
            logger.warning(f"Model {model_name} check failed: {e}")
            health.status = ModelHealthStatus.UNHEALTHY
            health.error = str(e)
            health.consecutive_failures = 1
        
        # Update stored state
        if model_name in self.models:
            existing = self.models[model_name]
            health.consecutive_failures = existing.consecutive_failures + (1 if health.status == ModelHealthStatus.UNHEALTHY else 0)
            
            # Update status based on consecutive failures
            threshold = self.config.get("health_check", {}).get("consecutive_failures_threshold", 3)
            if health.consecutive_failures >= threshold:
                health.status = ModelHealthStatus.UNHEALTHY
            elif health.consecutive_failures >= 1:
                health.status = ModelHealthStatus.DEGRADED
        
        self.models[model_name] = health
        return health

    def check_vram(self) -> VRAMInfo:
        """Check VRAM usage via nvidia-smi"""
        vram = VRAMInfo()
        
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total,memory.used,memory.free,temperature.gpu", "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0 and result.stdout.strip():
                parts = result.stdout.strip().split(",")
                if len(parts) >= 5:
                    vram.gpu_name = parts[0].strip()
                    vram.total_gb = float(parts[1].strip()) / 1024
                    vram.used_gb = float(parts[2].strip()) / 1024
                    vram.free_gb = float(parts[3].strip()) / 1024
                    vram.temperature_c = int(parts[4].strip())
                    
                    logger.debug(f"VRAM: {vram.used_gb:.1f}/{vram.total_gb:.1f}GB used, {vram.temperature_c}C")
                else:
                    logger.warning(f"Unexpected nvidia-smi output: {result.stdout}")
            else:
                logger.warning(f"nvidia-smi failed: {result.stderr}")
                
        except FileNotFoundError:
            logger.warning("nvidia-smi not found - VRAM check skipped")
        except subprocess.TimeoutExpired:
            logger.warning("nvidia-smi timed out")
        except Exception as e:
            logger.warning(f"VRAM check failed: {e}")
        
        self.vram_info = vram
        return vram

    def check_all(self) -> Dict[str, Any]:
        """Run all checks, return comprehensive health report"""
        logger.info("Running full health check...")
        
        # Check Ollama
        self.check_ollama()
        
        # Check local models
        models_config = self.config.get("models", {}).get("local", {})
        for model_name, model_config in models_config.items():
            provider = model_config.get("provider", "ollama")
            self.check_model(model_name, provider)
        
        # Check VRAM
        self.check_vram()
        
        # Save state
        self.save_state()
        
        return self.get_health_report()

    def is_model_healthy(self, model_name: str) -> bool:
        """Check if a model is healthy based on cached state"""
        if model_name not in self.models:
            return True  # Unknown models are considered healthy
        
        health = self.models[model_name]
        return health.status in (ModelHealthStatus.HEALTHY, ModelHealthStatus.DEGRADED)

    def get_health_report(self) -> Dict[str, Any]:
        """Return full JSON-serializable report"""
        # Calculate overall status
        healthy_count = sum(1 for m in self.models.values() if m.status == ModelHealthStatus.HEALTHY)
        degraded_count = sum(1 for m in self.models.values() if m.status == ModelHealthStatus.DEGRADED)
        unhealthy_count = sum(1 for m in self.models.values() if m.status == ModelHealthStatus.UNHEALTHY)
        unknown_count = sum(1 for m in self.models.values() if m.status == ModelHealthStatus.UNKNOWN)
        
        total_models = len(self.models)
        
        if total_models == 0:
            overall_status = "unknown"
        elif unhealthy_count > 0:
            overall_status = "critical"
        elif degraded_count > 0:
            overall_status = "degraded"
        else:
            overall_status = "healthy"
        
        return {
            "status": overall_status,
            "ollama_available": self.ollama_available,
            "vram": self.vram_info.to_dict(),
            "models": {
                name: model.to_dict()
                for name, model in self.models.items()
            },
            "summary": {
                "total": total_models,
                "healthy": healthy_count,
                "degraded": degraded_count,
                "unhealthy": unhealthy_count,
                "unknown": unknown_count
            },
            "timestamp": time.time()
        }

    def run_daemon(self, interval_seconds: int = 30) -> None:
        """Main loop - runs checks every N seconds"""
        logger.info(f"Starting health monitor daemon (interval: {interval_seconds}s)")
        
        try:
            while True:
                logger.debug("Running health check cycle...")
                self.check_all()
                time.sleep(interval_seconds)
        except KeyboardInterrupt:
            logger.info("Health monitor daemon stopped")
        except Exception as e:
            logger.error(f"Daemon error: {e}")
            # Never crash - continue on error
            time.sleep(interval_seconds)


def get_exit_code(status: str) -> int:
    """Map health status to exit code"""
    if status == "healthy":
        return 0
    elif status == "degraded":
        return 1
    else:  # critical or unknown
        return 2


def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(description="Model Health Monitor")
    parser.add_argument("--daemon", action="store_true", help="Run continuous monitoring loop")
    parser.add_argument("--once", action="store_true", help="Run single check and exit")
    parser.add_argument("--report", action="store_true", help="Load and display last saved state")
    parser.add_argument("--interval", type=int, default=30, help="Daemon interval in seconds")
    parser.add_argument("--config", default="configs/model_router.json", help="Config file path")
    parser.add_argument("--state", default=".sisyphus/model_health.json", help="State file path")
    
    args = parser.parse_args()
    
    # Setup basic logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        stream=sys.stderr
    )
    
    # Create monitor
    monitor = HealthMonitor(config_path=args.config, state_file=args.state)
    
    if args.report:
        # Load and display saved state
        monitor.load_state()
        report = monitor.get_health_report()
        print(json.dumps(report, indent=2))
        exit_code = get_exit_code(report["status"])
        sys.exit(exit_code)
    
    if args.daemon:
        # Run daemon loop
        monitor.run_daemon(interval_seconds=args.interval)
    else:
        # Default: single check
        report = monitor.check_all()
        print(json.dumps(report, indent=2))
        exit_code = get_exit_code(report["status"])
        sys.exit(exit_code)


if __name__ == "__main__":
    main()