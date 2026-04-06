"""Agent Execution Sandbox

Prevents agents from accessing sensitive files and executing dangerous commands.
"""

import os
import re
import logging
from pathlib import Path
from typing import List, Set, Optional, Tuple

logger = logging.getLogger("agent-sandbox")


class SandboxConfig:
    """Configuration for the agent sandbox."""
    
    def __init__(self):
        # Allowed directories
        self.allowed_dirs: List[str] = [
            str(Path(__file__).parent.parent.parent),  # Project root
        ]
        
        # Denied file patterns
        self.denied_patterns: List[str] = [
            r'\.env$',
            r'\.env\..*$',
            r'\.key$',
            r'\.pem$',
            r'\.crt$',
            r'passwords?\..*$',
            r'secrets?\..*$',
            r'credentials?\..*$',
            r'\.ssh/.*$',
            r'\.git/.*$',
            r'node_modules/.*$',
            r'__pycache__/.*$',
            r'\.pyc$',
        ]
        
        # Denied commands
        self.denied_commands: List[str] = [
            'rm -rf',
            'rm -rf /',
            'sudo',
            'mkfs',
            'dd if=',
            'chmod 777',
            'curl | sh',
            'wget | sh',
            'curl | bash',
            'wget | bash',
            'eval(',
            'exec(',
            '__import__',
        ]
        
        # File size limits (bytes)
        self.max_file_size: int = 10 * 1024 * 1024  # 10MB
        
        # Max files per operation
        self.max_files_per_op: int = 100


class AgentSandbox:
    """Sandbox for agent execution."""
    
    def __init__(self, config: Optional[SandboxConfig] = None):
        self.config = config or SandboxConfig()
        self._violations: List[dict] = []
    
    def check_file_access(self, file_path: str, operation: str = "read") -> Tuple[bool, str]:
        """Check if file access is allowed."""
        path = Path(file_path).resolve()
        
        # Check if file exists
        if operation in ["read", "write"] and not path.exists() and operation == "read":
            return False, f"File not found: {file_path}"
        
        # Check allowed directories
        allowed = False
        for allowed_dir in self.config.allowed_dirs:
            try:
                path.relative_to(Path(allowed_dir).resolve())
                allowed = True
                break
            except ValueError:
                continue
        
        if not allowed:
            self._log_violation("file_access", file_path, f"Outside allowed directories")
            return False, f"Access denied: {file_path} is outside allowed directories"
        
        # Check denied patterns
        for pattern in self.config.denied_patterns:
            if re.search(pattern, str(path)):
                self._log_violation("file_pattern", file_path, f"Matches denied pattern: {pattern}")
                return False, f"Access denied: {file_path} matches restricted pattern"
        
        # Check file size for reads
        if operation == "read" and path.exists():
            try:
                size = path.stat().st_size
                if size > self.config.max_file_size:
                    self._log_violation("file_size", file_path, f"File too large: {size} bytes")
                    return False, f"File too large: {size} bytes (max: {self.config.max_file_size})"
            except OSError:
                pass
        
        return True, "Access allowed"
    
    def check_command(self, command: str) -> Tuple[bool, str]:
        """Check if command execution is allowed."""
        # Check denied commands
        for denied in self.config.denied_commands:
            if denied.lower() in command.lower():
                self._log_violation("command", command, f"Contains denied command: {denied}")
                return False, f"Command denied: contains restricted pattern '{denied}'"
        
        return True, "Command allowed"
    
    def check_batch_operations(self, file_paths: List[str]) -> Tuple[bool, str]:
        """Check batch file operations."""
        if len(file_paths) > self.config.max_files_per_op:
            self._log_violation("batch_size", f"{len(file_paths)} files", f"Too many files: {len(file_paths)}")
            return False, f"Too many files: {len(file_paths)} (max: {self.config.max_files_per_op})"
        
        # Check each file
        for path in file_paths:
            allowed, reason = self.check_file_access(path)
            if not allowed:
                return False, reason
        
        return True, "Batch operation allowed"
    
    def _log_violation(self, violation_type: str, target: str, reason: str):
        """Log a sandbox violation."""
        import time
        self._violations.append({
            'type': violation_type,
            'target': target,
            'reason': reason,
            'timestamp': time.time()
        })
        logger.warning(f"Sandbox violation: {violation_type} - {target} - {reason}")
    
    def get_violations(self, limit: int = 10) -> List[dict]:
        """Get recent sandbox violations."""
        return self._violations[-limit:]
    
    def get_stats(self) -> dict:
        """Get sandbox statistics."""
        return {
            'total_violations': len(self._violations),
            'recent_violations': len(self._violations[-10:]),
            'allowed_dirs': self.config.allowed_dirs,
            'denied_patterns': len(self.config.denied_patterns),
            'denied_commands': len(self.config.denied_commands),
        }


# Global sandbox instance
_sandbox = None

def get_sandbox() -> AgentSandbox:
    """Get or create the global sandbox."""
    global _sandbox
    if _sandbox is None:
        _sandbox = AgentSandbox()
    return _sandbox
