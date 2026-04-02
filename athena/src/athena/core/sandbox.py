"""
athena.core.sandbox
===================

Docker Sandbox Execution for Law #1 (No Irreversible Ruin).
Extracted from OpenClaw's Host/Sandbox boundary ("The Great Steal 2.0").

Architecture:
  [athenad /sandbox/exec] --(docker run)--> [athena-sandbox container] --(stdout)--> [response]

Runs untrusted/experimental Python scripts in an isolated Docker container with:
  - No network access (--network none)
  - Read-only filesystem (--read-only)
  - Non-root user
  - Configurable timeout
  - Writable /tmp only via tmpfs
"""

import subprocess
import logging
import time
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any

from pydantic import BaseModel

logger = logging.getLogger("athenad")

SANDBOX_IMAGE = "athena-sandbox:latest"
DEFAULT_TIMEOUT = 30  # seconds


# --- Pydantic Models ---


class SandboxExecRequest(BaseModel):
    script: str  # Python script content
    timeout: int = DEFAULT_TIMEOUT
    allow_network: bool = False


class SandboxExecResponse(BaseModel):
    stdout: str
    stderr: str
    exit_code: int
    execution_time: float
    sandbox: str


# --- Sandbox Logic ---


class SandboxRunner:
    """Execute Python scripts inside an isolated Docker container."""

    def __init__(self, image: str = SANDBOX_IMAGE):
        self.image = image

    def is_available(self) -> bool:
        """Check if Docker is available and the sandbox image exists."""
        try:
            result = subprocess.run(
                ["docker", "image", "inspect", self.image],
                capture_output=True,
                timeout=5,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def execute(self, request: SandboxExecRequest) -> SandboxExecResponse:
        """Run a Python script inside the sandbox container."""
        start_time = time.time()

        # Write script to a temp file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, prefix="athena_sandbox_"
        ) as f:
            f.write(request.script)
            script_path = f.name

        # Build docker command
        docker_cmd = [
            "docker",
            "run",
            "--rm",  # Clean up container after execution
            "--read-only",  # Read-only root filesystem
            "--tmpfs",
            "/tmp:rw,size=64m",  # Writable temp dir (64MB max)
            "--memory",
            "256m",  # Memory limit
            "--cpus",
            "1.0",  # CPU limit
            "-v",
            f"{script_path}:/workspace/script.py:ro",  # Mount script read-only
        ]

        # Network isolation (default: no network)
        if not request.allow_network:
            docker_cmd.extend(["--network", "none"])

        docker_cmd.extend(
            [
                self.image,
                "python3",
                "/workspace/script.py",
            ]
        )

        try:
            result = subprocess.run(
                docker_cmd,
                capture_output=True,
                text=True,
                timeout=request.timeout,
            )
            execution_time = time.time() - start_time

            logger.info(
                f"🐳 Sandbox exec completed: exit={result.returncode}, "
                f"time={execution_time:.2f}s"
            )

            return SandboxExecResponse(
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode,
                execution_time=execution_time,
                sandbox=self.image,
            )

        except subprocess.TimeoutExpired:
            execution_time = time.time() - start_time
            logger.warning(f"⏰ Sandbox exec timed out after {request.timeout}s")
            return SandboxExecResponse(
                stdout="",
                stderr=f"Execution timed out after {request.timeout} seconds.",
                exit_code=-1,
                execution_time=execution_time,
                sandbox=self.image,
            )

        except FileNotFoundError:
            return SandboxExecResponse(
                stdout="",
                stderr="Docker is not installed or not in PATH.",
                exit_code=-2,
                execution_time=0.0,
                sandbox=self.image,
            )

        finally:
            # Clean up temp file
            try:
                Path(script_path).unlink()
            except OSError:
                pass


# Singleton runner
sandbox_runner = SandboxRunner()
