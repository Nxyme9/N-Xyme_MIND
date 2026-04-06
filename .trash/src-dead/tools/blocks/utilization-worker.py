#!/usr/bin/env python3
"""
Utilization Worker - Maximize CPU and GPU utilization for N-Xyme Catalyst.

RTX 3080 Ti Specs:
- 12GB VRAM
- 10240 CUDA cores
- Target: 60-80% GPU compute

AMD Ryzen 7 7800X3D:
- 8 cores / 16 threads
- 104MB cache
- Target: 70% CPU usage

Usage:
    python scripts/utilization-worker.py              # Start workers
    python scripts/utilization-worker.py --status     # Check status
    python scripts/utilization-worker.py --stop       # Stop workers
    python scripts/utilization-worker.py --benchmark  # Run benchmark
"""

import json
import os
import subprocess
import sys
import time
import threading
import queue
import hashlib
import gzip
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/utilization-worker.log", mode="a"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# Import centralized configuration
try:
    from jarvis.config.graphiti_config import OLLAMA_URL
except ImportError:
    OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")

# Constants
WORKSPACE_ROOT = Path(__file__).parent.parent
DATA_DIR = WORKSPACE_ROOT / "data"
LOGS_DIR = WORKSPACE_ROOT / "logs"
INDEX_DIR = DATA_DIR / "index"
EMBEDDINGS_DIR = DATA_DIR / "embeddings"

# Ensure directories exist
for dir_path in [DATA_DIR, LOGS_DIR, INDEX_DIR, EMBEDDINGS_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# Model configurations
GPU_MODELS = {
    "embedding": {
        "name": "nomic-embed-text:latest",
        "size_gb": 0.3,
        "priority": 1,
        "task_type": "embedding",
    },
    "fast": {
        "name": "llama3.2:3b-instruct-q4_K_M",
        "size_gb": 2.0,
        "priority": 2,
        "task_type": "chat",
    },
    "coding": {"name": "qwen2.5-coder:7b", "size_gb": 4.7, "priority": 3, "task_type": "chat"},
    "vision": {"name": "llava:7b", "size_gb": 4.7, "priority": 4, "task_type": "vision"},
}

# Prompts for continuous GPU tasks
CHAT_PROMPTS = [
    "Analyze this code snippet and suggest improvements: def factorial(n): return n * factorial(n-1) if n > 1 else 1",
    "What are the best practices for error handling in Python?",
    "Explain the difference between async and sync programming.",
    "Write a function to merge two sorted lists.",
    "What is the time complexity of quicksort and why?",
    "Describe the SOLID principles in software design.",
    "How does garbage collection work in Python?",
    "Explain the concept of dependency injection.",
    "What are design patterns and when should you use them?",
    "Write a Python decorator for caching function results.",
]

EMBEDDING_TEXTS = [
    "def calculate_fibonacci(n): return calculate_fibonacci(n-1) + calculate_fibonacci(n-2) if n > 1 else n",
    "class DataProcessor: def __init__(self): self.data = [] def process(self): pass",
    "import numpy as np; import pandas as pd; df = pd.DataFrame()",
    "async def fetch_data(url): async with aiohttp.ClientSession() as session: return await session.get(url)",
    "SELECT * FROM users WHERE active = true ORDER BY created_at DESC LIMIT 100",
]


@dataclass
class WorkerStats:
    """Statistics for worker performance."""

    tasks_completed: int = 0
    tasks_failed: int = 0
    total_time_ms: float = 0
    avg_time_ms: float = 0
    last_task_time: Optional[str] = None
    current_task: Optional[str] = None
    status: str = "idle"


class GPUWorker:
    """GPU worker for continuous inference tasks."""

    def __init__(self, worker_id: int):
        self.worker_id = worker_id
        self.stats = WorkerStats()
        self.running = False
        self.task_queue = queue.Queue()
        self.thread: Optional[threading.Thread] = None

    def start(self):
        """Start the GPU worker thread."""
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        logger.info(f"GPU Worker {self.worker_id} started")

    def stop(self):
        """Stop the GPU worker thread."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info(f"GPU Worker {self.worker_id} stopped")

    def _run(self):
        """Main worker loop."""
        import requests

        while self.running:
            try:
                # Get a task from queue or generate one
                try:
                    task = self.task_queue.get(timeout=1)
                except queue.Empty:
                    task = self._generate_task()

                if task:
                    self.stats.current_task = task["type"]
                    self.stats.status = "running"
                    start_time = time.time()

                    try:
                        self._execute_task(task, requests)
                        self.stats.tasks_completed += 1
                    except Exception as e:
                        self.stats.tasks_failed += 1
                        logger.error(f"GPU Worker {self.worker_id} task failed: {e}")

                    elapsed_ms = (time.time() - start_time) * 1000
                    self.stats.total_time_ms += elapsed_ms
                    self.stats.avg_time_ms = self.stats.total_time_ms / max(
                        1, self.stats.tasks_completed
                    )
                    self.stats.last_task_time = datetime.now().isoformat()
                    self.stats.current_task = None
                    self.stats.status = "idle"

            except Exception as e:
                logger.error(f"GPU Worker {self.worker_id} error: {e}")
                time.sleep(1)

    def _generate_task(self) -> Optional[Dict[str, Any]]:
        """Generate a GPU task based on available models."""
        import requests

        try:
            # Check loaded models
            resp = requests.get(f"{OLLAMA_URL}/api/ps", timeout=5)
            loaded = resp.json().get("models", [])
            loaded_names = {m["name"] for m in loaded}

            # Pick a task based on loaded models
            if "nomic-embed-text:latest" in loaded_names:
                return {
                    "type": "embedding",
                    "model": "nomic-embed-text:latest",
                    "text": EMBEDDING_TEXTS[self.stats.tasks_completed % len(EMBEDDING_TEXTS)],
                }
            elif "llava:7b" in loaded_names:
                return {
                    "type": "vision",
                    "model": "llava:7b",
                    "prompt": "Describe this code structure and its purpose.",
                }
            elif any(
                m in loaded_names for m in ["llama3.2:3b-instruct-q4_K_M", "qwen2.5-coder:7b"]
            ):
                model = (
                    "llama3.2:3b-instruct-q4_K_M"
                    if "llama3.2:3b-instruct-q4_K_M" in loaded_names
                    else "qwen2.5-coder:7b"
                )
                return {
                    "type": "chat",
                    "model": model,
                    "prompt": CHAT_PROMPTS[self.stats.tasks_completed % len(CHAT_PROMPTS)],
                }
            else:
                # No models loaded, try to load one
                return {"type": "load_model", "model": "nomic-embed-text:latest"}
        except Exception as e:
            logger.error(f"Failed to generate task: {e}")
            return None

    def _execute_task(self, task: Dict[str, Any], requests_module):
        """Execute a GPU task."""
        task_type = task["type"]

        if task_type == "embedding":
            resp = requests_module.post(
                f"{OLLAMA_URL}/api/embeddings",
                json={"model": task["model"], "prompt": task["text"]},
                timeout=30,
            )
            if resp.status_code == 200:
                embedding = resp.json().get("embedding", [])
                # Save embedding
                self._save_embedding(task["text"], embedding)

        elif task_type == "chat":
            resp = requests_module.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": task["model"],
                    "prompt": task["prompt"],
                    "stream": False,
                    "options": {"num_predict": 100},
                },
                timeout=60,
            )

        elif task_type == "vision":
            # For vision tasks, we'd need an image
            # For now, just run a text generation
            resp = requests_module.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": task["model"],
                    "prompt": task["prompt"],
                    "stream": False,
                    "options": {"num_predict": 50},
                },
                timeout=60,
            )

        elif task_type == "load_model":
            resp = requests_module.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": task["model"],
                    "prompt": "ready",
                    "stream": False,
                    "options": {"num_predict": 1},
                },
                timeout=120,
            )

    def _save_embedding(self, text: str, embedding: List[float]):
        """Save embedding to disk."""
        try:
            text_hash = hashlib.md5(text.encode()).hexdigest()
            embedding_file = EMBEDDINGS_DIR / f"{text_hash}.json"

            data = {"text": text, "embedding": embedding, "timestamp": datetime.now().isoformat()}

            with open(embedding_file, "w") as f:
                json.dump(data, f)
        except Exception as e:
            logger.error(f"Failed to save embedding: {e}")


class CPUWorker:
    """CPU worker for file indexing and analysis tasks."""

    def __init__(self, worker_id: int):
        self.worker_id = worker_id
        self.stats = WorkerStats()
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.task_generators = [
            self._index_python_files,
            self._validate_configs,
            self._compress_old_logs,
            self._analyze_dependencies,
            self._index_markdown_files,
            self._check_syntax,
        ]
        self.current_generator_idx = 0

    def start(self):
        """Start the CPU worker thread."""
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        logger.info(f"CPU Worker {self.worker_id} started")

    def stop(self):
        """Stop the CPU worker thread."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info(f"CPU Worker {self.worker_id} stopped")

    def _run(self):
        """Main worker loop."""
        while self.running:
            try:
                # Get next task generator
                generator = self.task_generators[self.current_generator_idx]
                self.current_generator_idx = (self.current_generator_idx + 1) % len(
                    self.task_generators
                )

                self.stats.current_task = generator.__name__
                self.stats.status = "running"
                start_time = time.time()

                try:
                    generator()
                    self.stats.tasks_completed += 1
                except Exception as e:
                    self.stats.tasks_failed += 1
                    logger.error(f"CPU Worker {self.worker_id} task failed: {e}")

                elapsed_ms = (time.time() - start_time) * 1000
                self.stats.total_time_ms += elapsed_ms
                self.stats.avg_time_ms = self.stats.total_time_ms / max(
                    1, self.stats.tasks_completed
                )
                self.stats.last_task_time = datetime.now().isoformat()
                self.stats.current_task = None
                self.stats.status = "idle"

                # Small delay between tasks
                time.sleep(0.5)

            except Exception as e:
                logger.error(f"CPU Worker {self.worker_id} error: {e}")
                time.sleep(1)

    def _index_python_files(self):
        """Index all Python files in the workspace."""
        logger.info(f"CPU Worker {self.worker_id}: Indexing Python files...")

        index_data = {"timestamp": datetime.now().isoformat(), "files": []}

        for py_file in WORKSPACE_ROOT.rglob("*.py"):
            if ".git" in str(py_file) or "node_modules" in str(py_file):
                continue

            try:
                stat = py_file.stat()
                with open(py_file, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                # Extract basic info
                lines = content.split("\n")
                imports = [l for l in lines if l.strip().startswith(("import ", "from "))]
                functions = [l for l in lines if l.strip().startswith("def ")]
                classes = [l for l in lines if l.strip().startswith("class ")]

                index_data["files"].append(
                    {
                        "path": str(py_file.relative_to(WORKSPACE_ROOT)),
                        "size_bytes": stat.st_size,
                        "lines": len(lines),
                        "imports": len(imports),
                        "functions": len(functions),
                        "classes": len(classes),
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    }
                )
            except Exception as e:
                logger.debug(f"Failed to index {py_file}: {e}")

        # Save index
        index_file = INDEX_DIR / "python_files.json"
        with open(index_file, "w") as f:
            json.dump(index_data, f, indent=2)

        logger.info(f"CPU Worker {self.worker_id}: Indexed {len(index_data['files'])} Python files")

    def _validate_configs(self):
        """Validate configuration files."""
        logger.info(f"CPU Worker {self.worker_id}: Validating configs...")

        config_dirs = [
            WORKSPACE_ROOT / "config",
            WORKSPACE_ROOT / "configs",
            WORKSPACE_ROOT / ".config",
        ]

        results = {"timestamp": datetime.now().isoformat(), "valid": [], "invalid": []}

        for config_dir in config_dirs:
            if not config_dir.exists():
                continue

            for config_file in config_dir.rglob("*"):
                if config_file.is_file():
                    try:
                        if config_file.suffix == ".json":
                            with open(config_file, "r") as f:
                                json.load(f)
                            results["valid"].append(str(config_file.relative_to(WORKSPACE_ROOT)))
                        elif config_file.suffix in [".yaml", ".yml"]:
                            # Basic YAML validation (check for common issues)
                            with open(config_file, "r") as f:
                                content = f.read()
                                if content.strip():
                                    results["valid"].append(
                                        str(config_file.relative_to(WORKSPACE_ROOT))
                                    )
                    except json.JSONDecodeError as e:
                        results["invalid"].append(
                            {"file": str(config_file.relative_to(WORKSPACE_ROOT)), "error": str(e)}
                        )
                    except Exception as e:
                        logger.debug(f"Failed to validate {config_file}: {e}")

        # Save results
        results_file = INDEX_DIR / "config_validation.json"
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2)

        logger.info(
            f"CPU Worker {self.worker_id}: Validated {len(results['valid'])} configs, {len(results['invalid'])} invalid"
        )

    def _compress_old_logs(self):
        """Compress log files older than 1 day."""
        logger.info(f"CPU Worker {self.worker_id}: Compressing old logs...")

        if not LOGS_DIR.exists():
            return

        compressed_count = 0
        cutoff_time = time.time() - (24 * 60 * 60)  # 1 day ago

        for log_file in LOGS_DIR.glob("*.log"):
            try:
                if log_file.stat().st_mtime < cutoff_time:
                    gz_file = log_file.with_suffix(".log.gz")

                    if not gz_file.exists():
                        with open(log_file, "rb") as f_in:
                            with gzip.open(gz_file, "wb") as f_out:
                                shutil.copyfileobj(f_in, f_out)

                        # Remove original after successful compression
                        log_file.unlink()
                        compressed_count += 1

            except Exception as e:
                logger.debug(f"Failed to compress {log_file}: {e}")

        logger.info(f"CPU Worker {self.worker_id}: Compressed {compressed_count} log files")

    def _analyze_dependencies(self):
        """Analyze project dependencies."""
        logger.info(f"CPU Worker {self.worker_id}: Analyzing dependencies...")

        deps = {"timestamp": datetime.now().isoformat(), "python": {}, "node": {}}

        # Python dependencies
        req_files = [WORKSPACE_ROOT / "requirements.txt", WORKSPACE_ROOT / "pyproject.toml"]

        for req_file in req_files:
            if req_file.exists():
                try:
                    with open(req_file, "r") as f:
                        content = f.read()

                    if req_file.name == "requirements.txt":
                        packages = [
                            l.strip()
                            for l in content.split("\n")
                            if l.strip() and not l.startswith("#")
                        ]
                        deps["python"]["requirements.txt"] = packages
                    elif req_file.name == "pyproject.toml":
                        deps["python"]["pyproject.toml"] = "exists"
                except Exception as e:
                    logger.debug(f"Failed to read {req_file}: {e}")

        # Node dependencies
        package_json = WORKSPACE_ROOT / "package.json"
        if package_json.exists():
            try:
                with open(package_json, "r") as f:
                    pkg = json.load(f)
                    deps["node"]["dependencies"] = len(pkg.get("dependencies", {}))
                    deps["node"]["devDependencies"] = len(pkg.get("devDependencies", {}))
            except Exception as e:
                logger.debug(f"Failed to read package.json: {e}")

        # Save analysis
        deps_file = INDEX_DIR / "dependencies.json"
        with open(deps_file, "w") as f:
            json.dump(deps, f, indent=2)

        logger.info(f"CPU Worker {self.worker_id}: Dependency analysis complete")

    def _index_markdown_files(self):
        """Index all Markdown files."""
        logger.info(f"CPU Worker {self.worker_id}: Indexing Markdown files...")

        index_data = {"timestamp": datetime.now().isoformat(), "files": []}

        for md_file in WORKSPACE_ROOT.rglob("*.md"):
            if ".git" in str(md_file) or "node_modules" in str(md_file):
                continue

            try:
                stat = md_file.stat()
                with open(md_file, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                # Extract headers
                lines = content.split("\n")
                headers = [l for l in lines if l.startswith("#")]

                index_data["files"].append(
                    {
                        "path": str(md_file.relative_to(WORKSPACE_ROOT)),
                        "size_bytes": stat.st_size,
                        "lines": len(lines),
                        "headers": len(headers),
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    }
                )
            except Exception as e:
                logger.debug(f"Failed to index {md_file}: {e}")

        # Save index
        index_file = INDEX_DIR / "markdown_files.json"
        with open(index_file, "w") as f:
            json.dump(index_data, f, indent=2)

        logger.info(
            f"CPU Worker {self.worker_id}: Indexed {len(index_data['files'])} Markdown files"
        )

    def _check_syntax(self):
        """Check Python file syntax."""
        logger.info(f"CPU Worker {self.worker_id}: Checking Python syntax...")

        results = {"timestamp": datetime.now().isoformat(), "valid": [], "invalid": []}

        for py_file in WORKSPACE_ROOT.rglob("*.py"):
            if ".git" in str(py_file) or "node_modules" in str(py_file):
                continue

            try:
                result = subprocess.run(
                    [sys.executable, "-m", "py_compile", str(py_file)],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

                rel_path = str(py_file.relative_to(WORKSPACE_ROOT))
                if result.returncode == 0:
                    results["valid"].append(rel_path)
                else:
                    results["invalid"].append({"file": rel_path, "error": result.stderr})
            except Exception as e:
                logger.debug(f"Failed to check {py_file}: {e}")

        # Save results
        results_file = INDEX_DIR / "syntax_check.json"
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2)

        logger.info(
            f"CPU Worker {self.worker_id}: Checked {len(results['valid'])} files, {len(results['invalid'])} invalid"
        )


class UtilizationScheduler:
    """Scheduler to balance GPU and CPU workload."""

    def __init__(self, gpu_workers: int = 2, cpu_workers: int = 4):
        self.gpu_workers = [GPUWorker(i) for i in range(gpu_workers)]
        self.cpu_workers = [CPUWorker(i) for i in range(cpu_workers)]
        self.running = False
        self.monitor_thread: Optional[threading.Thread] = None

    def start(self):
        """Start all workers and monitoring."""
        logger.info("Starting Utilization Scheduler...")

        self.running = True

        # Start GPU workers
        for worker in self.gpu_workers:
            worker.start()

        # Start CPU workers
        for worker in self.cpu_workers:
            worker.start()

        # Start monitor thread
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()

        logger.info(
            f"Scheduler started: {len(self.gpu_workers)} GPU workers, {len(self.cpu_workers)} CPU workers"
        )

    def stop(self):
        """Stop all workers."""
        logger.info("Stopping Utilization Scheduler...")

        self.running = False

        # Stop GPU workers
        for worker in self.gpu_workers:
            worker.stop()

        # Stop CPU workers
        for worker in self.cpu_workers:
            worker.stop()

        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)

        logger.info("Scheduler stopped")

    def _monitor_loop(self):
        """Monitor and log utilization."""
        while self.running:
            try:
                self._log_status()
                time.sleep(10)  # Log every 10 seconds
            except Exception as e:
                logger.error(f"Monitor error: {e}")
                time.sleep(5)

    def _log_status(self):
        """Log current status of all workers."""
        gpu_status = []
        for worker in self.gpu_workers:
            gpu_status.append(
                {
                    "id": worker.worker_id,
                    "status": worker.stats.status,
                    "completed": worker.stats.tasks_completed,
                    "failed": worker.stats.tasks_failed,
                    "avg_time_ms": round(worker.stats.avg_time_ms, 2),
                }
            )

        cpu_status = []
        for worker in self.cpu_workers:
            cpu_status.append(
                {
                    "id": worker.worker_id,
                    "status": worker.stats.status,
                    "completed": worker.stats.tasks_completed,
                    "failed": worker.stats.tasks_failed,
                    "avg_time_ms": round(worker.stats.avg_time_ms, 2),
                }
            )

        # Get hardware status
        gpu_hw = get_gpu_status()
        cpu_hw = get_cpu_status()

        status = {
            "timestamp": datetime.now().isoformat(),
            "gpu_workers": gpu_status,
            "cpu_workers": cpu_status,
            "hardware": {
                "gpu_util": gpu_hw.get("utilization_percent", 0),
                "gpu_temp": gpu_hw.get("temperature_c", 0),
                "cpu_util": cpu_hw.get("load_pct", 0),
            },
        }

        # Save status
        status_file = DATA_DIR / "utilization_status.json"
        with open(status_file, "w") as f:
            json.dump(status, f, indent=2)

    def get_status(self) -> Dict[str, Any]:
        """Get current scheduler status."""
        gpu_status = []
        total_gpu_completed = 0
        total_gpu_failed = 0

        for worker in self.gpu_workers:
            gpu_status.append(asdict(worker.stats))
            total_gpu_completed += worker.stats.tasks_completed
            total_gpu_failed += worker.stats.tasks_failed

        cpu_status = []
        total_cpu_completed = 0
        total_cpu_failed = 0

        for worker in self.cpu_workers:
            cpu_status.append(asdict(worker.stats))
            total_cpu_completed += worker.stats.tasks_completed
            total_cpu_failed += worker.stats.tasks_failed

        return {
            "running": self.running,
            "gpu_workers": {
                "count": len(self.gpu_workers),
                "total_completed": total_gpu_completed,
                "total_failed": total_gpu_failed,
                "details": gpu_status,
            },
            "cpu_workers": {
                "count": len(self.cpu_workers),
                "total_completed": total_cpu_completed,
                "total_failed": total_cpu_failed,
                "details": cpu_status,
            },
        }


def get_gpu_status() -> Dict[str, Any]:
    """Get current GPU status."""
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.used,memory.total,utilization.gpu,temperature.gpu",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            parts = result.stdout.strip().split(", ")
            return {
                "name": parts[0],
                "memory_used_mb": int(parts[1]),
                "memory_total_mb": int(parts[2]),
                "utilization_percent": int(parts[3]),
                "temperature_c": int(parts[4]),
                "memory_free_mb": int(parts[2]) - int(parts[1]),
                "memory_used_percent": round(int(parts[1]) / int(parts[2]) * 100, 1),
            }
    except Exception as e:
        logger.error(f"Error getting GPU status: {e}")
    return {}


def get_cpu_status() -> Dict[str, Any]:
    """Get current CPU status."""
    try:
        import psutil

        f = psutil.cpu_freq()
        return {
            "cores": psutil.cpu_count(False),
            "threads": psutil.cpu_count(True),
            "load_pct": psutil.cpu_percent(interval=0.1),
            "freq_mhz": round(f.current) if f else 0,
        }
    except Exception as e:
        logger.error(f"Error getting CPU status: {e}")
    return {}


def run_benchmark():
    """Run a benchmark to measure GPU and CPU performance."""
    import requests

    print("=" * 60)
    print("UTILIZATION WORKER BENCHMARK")
    print("=" * 60)

    # GPU Benchmark
    print("\n[GPU BENCHMARK]")
    gpu_before = get_gpu_status()
    print(f"GPU Before: {gpu_before.get('utilization_percent', 0)}% utilization")

    models_to_test = [
        "nomic-embed-text:latest",
        "llama3.2:3b-instruct-q4_K_M",
    ]

    for model in models_to_test:
        print(f"\nTesting {model}...")
        start = time.time()

        try:
            if model == "nomic-embed-text:latest":
                resp = requests.post(
                    f"{OLLAMA_URL}/api/embeddings",
                    json={"model": model, "prompt": "Test embedding generation"},
                    timeout=30,
                )
            else:
                resp = requests.post(
                    f"{OLLAMA_URL}/api/generate",
                    json={
                        "model": model,
                        "prompt": "Write a hello world function.",
                        "stream": False,
                        "options": {"num_predict": 50},
                    },
                    timeout=60,
                )

            elapsed = time.time() - start
            print(f"  Time: {elapsed:.2f}s")
            print(f"  Status: {'OK' if resp.status_code == 200 else 'FAIL'}")

        except Exception as e:
            print(f"  Error: {e}")

    gpu_after = get_gpu_status()
    print(f"\nGPU After: {gpu_after.get('utilization_percent', 0)}% utilization")

    # CPU Benchmark
    print("\n[CPU BENCHMARK]")
    cpu_before = get_cpu_status()
    print(f"CPU Before: {cpu_before.get('load_pct', 0)}% load")

    # Run CPU tasks
    worker = CPUWorker(0)

    tasks = [
        ("Index Python files", worker._index_python_files),
        ("Validate configs", worker._validate_configs),
        ("Analyze dependencies", worker._analyze_dependencies),
    ]

    for name, task in tasks:
        print(f"\nRunning {name}...")
        start = time.time()
        try:
            task()
            elapsed = time.time() - start
            print(f"  Time: {elapsed:.2f}s")
        except Exception as e:
            print(f"  Error: {e}")

    cpu_after = get_cpu_status()
    print(f"\nCPU After: {cpu_after.get('load_pct', 0)}% load")

    print("\n" + "=" * 60)
    print("BENCHMARK COMPLETE")
    print("=" * 60)


# Global scheduler instance
_scheduler: Optional[UtilizationScheduler] = None


def main():
    global _scheduler

    if len(sys.argv) > 1:
        arg = sys.argv[1]

        if arg == "--status":
            # Show status
            status_file = DATA_DIR / "utilization_status.json"
            if status_file.exists():
                with open(status_file, "r") as f:
                    status = json.load(f)
                    print(json.dumps(status, indent=2))
            else:
                print("No status file found. Is the worker running?")

        elif arg == "--stop":
            # Stop workers
            pid_file = DATA_DIR / "utilization_worker.pid"
            if pid_file.exists():
                with open(pid_file, "r") as f:
                    pid = int(f.read().strip())
                try:
                    os.kill(pid, 15)  # SIGTERM
                    print(f"Sent stop signal to PID {pid}")
                except ProcessLookupError:
                    print(f"Process {pid} not found")
                pid_file.unlink()
            else:
                print("No PID file found. Is the worker running?")

        elif arg == "--benchmark":
            run_benchmark()

        else:
            print(f"Unknown option: {arg}")
            print("Usage: utilization-worker.py [--status|--stop|--benchmark]")

    else:
        # Start workers
        print("=" * 60)
        print("UTILIZATION WORKER - Starting...")
        print("=" * 60)

        # Check GPU
        gpu = get_gpu_status()
        if gpu:
            print(f"\nGPU: {gpu.get('name', 'Unknown')}")
            print(f"VRAM: {gpu.get('memory_used_mb', 0)}MB / {gpu.get('memory_total_mb', 0)}MB")
            print(f"Utilization: {gpu.get('utilization_percent', 0)}%")
        else:
            print("\nWARNING: Could not detect GPU")

        # Check CPU
        cpu = get_cpu_status()
        print(f"\nCPU: {cpu.get('cores', 0)} cores / {cpu.get('threads', 0)} threads")
        print(f"Load: {cpu.get('load_pct', 0)}%")

        # Check Ollama
        try:
            import requests

            resp = requests.get(f"{OLLAMA_URL}/api/ps", timeout=5)
            models = resp.json().get("models", [])
            print(f"\nOllama: {len(models)} model(s) loaded")
            for m in models:
                size_gb = m.get("size_vram", 0) / 1e9
                print(f"  - {m['name']} ({size_gb:.1f}GB VRAM)")
        except Exception as e:
            print(f"\nWARNING: Could not connect to Ollama: {e}")

        # Save PID
        pid_file = DATA_DIR / "utilization_worker.pid"
        with open(pid_file, "w") as f:
            f.write(str(os.getpid()))

        print("\n" + "=" * 60)
        print("Starting workers... (Press Ctrl+C to stop)")
        print("=" * 60)

        # Start scheduler
        _scheduler = UtilizationScheduler(gpu_workers=2, cpu_workers=4)
        _scheduler.start()

        try:
            # Keep main thread alive
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\nStopping workers...")
            _scheduler.stop()
            if pid_file.exists():
                pid_file.unlink()
            print("Done.")


if __name__ == "__main__":
    main()
