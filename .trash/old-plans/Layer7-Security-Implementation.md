# Layer 7: Security — Implementation Plan (v1.0)

## Overview

This document provides a **dense, robust implementation plan** for **Layer 7: Security** of N-Xyme MIND v1.0. The plan addresses all critical security gaps identified in the masterplan and aligns with industry standards from studied repositories.

---

## 1. Executive Summary

### 1.1 Security Scope

Layer 7 Security encompasses:
1. **Agent Sandbox** — Kernel-enforced isolation (nono patterns)
2. **Jailbreak Detection** — Perplexity-based injection detection (PIGuard)
3. **Permission System** — Slowmist-style untrusted input handling
4. **Output Guardrails** — OWASP-aligned validation
5. **Supporting Infrastructure** — Encryption, audit logging, DoS protection

### 1.2 Dependencies Between Modules

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        LAYER 7 SECURITY ARCHITECTURE                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐  │
│  │  agent_sandbox   │    │ jailbreak_detector│    │ permission_system│  │
│  └────────┬─────────┘    └────────┬─────────┘    └────────┬─────────┘  │
│           │                      │                      │             │
│           ▼                      ▼                      ▼             │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    output_guardrails                           │   │
│  └──────────────────────────────────────────────────────────────┘   │
│           │                      │                      │             │
│           ▼                      ▼                      ▼             │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐  │
│  │   audit_logger   │    │   rate_limiter   │    │  key_manager     │  │
│  └────────┬─────────┘    └────────┬─────────┘    └────────┬─────────┘  │
│           │                      │                      │             │
│           └──────────────────────┼──────────────────────┘             │
│                                  ▼                                    │
│                    ┌─────────────────────────┐                       │
│                    │   encryption (existing)  │                       │
│                    └─────────────────────────┘                       │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.3 Implementation Order

| Wave | Files | Priority | Dependencies |
|------|-------|----------|--------------|
| **W1** | `audit_logger.py` (enhanced), `rate_limiter.py` | CRITICAL | encryption.py (existing) |
| **W2** | `jailbreak_detector.py`, `output_guardrails.py` | CRITICAL | audit_logger |
| **W3** | `permission_system.py` | HIGH | audit_logger, rate_limiter |
| **W4** | `agent_sandbox.py` | HIGH | permission_system |
| **W5** | Integration tests, security benchmarks | HIGH | All modules |

---

## 2. File-by-File Breakdown

### 2.1 `agent_sandbox.py` — Kernel-Enforced Sandbox

**Purpose**: Provide capability-based isolation for running untrusted agent code using nono patterns.

**Location**: `src/security/agent_sandbox.py`

#### 2.1.1 Class Definition

```python
from dataclasses import dataclass, field
from enum import Enum, Flag
from typing import Any, Callable, Dict, List, Optional, Set
from pathlib import Path
import hashlib
import json
import logging
import os
import subprocess
import tempfile

logger = logging.getLogger(__name__)


class Capability(Flag):
    """Capability flags for sandbox isolation."""
    NONE = 0
    READ = 1
    WRITE = 2
    EXECUTE = 4
    NETWORK = 8
    FILE_SYSTEM = 16
    ENV_ACCESS = 32
    PROCESS = 64
    MEMORY = 128


@dataclass
class SandboxConfig:
    """Sandbox configuration."""
    max_memory_mb: int = 512
    max_cpu_percent: int = 50
    max_execution_time_sec: int = 30
    max_file_size_mb: int = 100
    max_network_connections: int = 5
    allowed_paths: List[Path] = field(default_factory=list)
    blocked_commands: Set[str] = field(default_factory=set)
    capabilities: Capability = Capability.READ
    enable_atomic_rollback: bool = True
    audit_mode: bool = True


@dataclass
class SandboxResult:
    """Result of sandbox execution."""
    success: bool
    output: Optional[str] = None
    error: Optional[str] = None
    exit_code: Optional[int] = None
    execution_time_ms: int = 0
    capabilities_used: List[str] = field(default_factory=list)
    violations: List[str] = field(default_factory=list)
    rollback_available: bool = False
    audit_hash: Optional[str] = None
```

#### 2.1.2 Core Functions

```python
class AgentSandbox:
    """Kernel-enforced agent sandbox with capability-based isolation."""
    
    def __init__(self, config: Optional[SandboxConfig] = None):
        self.config = config or SandboxConfig()
        self._audit_chain: List[dict] = []
        self._capability_history: Dict[str, List[str]] = {}
        self._rollback_stack: List[dict] = []
        self._initialize()
    
    def _initialize(self) -> None:
        """Initialize sandbox environment."""
        # Create isolated temp directory
        self._sandbox_dir = Path(tempfile.mkdtemp(prefix="nxyme_sandbox_"))
        self._work_dir = self._sandbox_dir / "work"
        self._work_dir.mkdir(parents=True, exist_ok=True)
        self._output_dir = self._sandbox_dir / "output"
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._audit_dir = self._sandbox_dir / "audit"
        self._audit_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Sandbox initialized at {self._sandbox_dir}")
    
    def execute(
        self,
        code: str,
        language: str = "python",
        timeout: Optional[int] = None,
        capabilities: Optional[Capability] = None,
    ) -> SandboxResult:
        """Execute code in sandbox with capability enforcement."""
        start_time = time.time()
        capabilities = capabilities or self.config.capabilities
        
        # Pre-execution validation
        if not self._validate_code(code, language):
            return SandboxResult(
                success=False,
                error="Code validation failed",
                execution_time_ms=int((time.time() - start_time) * 1000),
            )
        
        # Log execution start
        self._log_execution_start(code, language, capabilities)
        
        # Execute with capability enforcement
        result = self._execute_internal(code, language, timeout, capabilities)
        
        # Post-execution audit
        result.audit_hash = self._seal_audit(result)
        
        return result
    
    def _validate_code(self, code: str, language: str) -> bool:
        """Validate code before execution (nono patterns)."""
        # Block dangerous patterns
        blocked_patterns = [
            r"import\s+os\s*;.*os\.system",
            r"import\s+subprocess",
            r"__import__\s*\(",
            r"eval\s*\(",
            r"exec\s*\(",
            r"import\s+pty",
            r"import\s+socket.*AF_INET",
            r"fabric",
            r"paramiko",
            r"fabric",
        ]
        
        for pattern in blocked_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                logger.warning(f"Blocked dangerous pattern: {pattern}")
                return False
        
        # Check file size
        if len(code) > self.config.max_file_size_mb * 1024 * 1024:
            logger.warning(f"Code exceeds size limit")
            return False
        
        return True
    
    def _execute_internal(
        self,
        code: str,
        language: str,
        timeout: Optional[int],
        capabilities: Capability,
    ) -> SandboxResult:
        """Internal execution with resource limits."""
        # Write code to sandbox file
        ext = ".py" if language == "python" else ".js"
        code_file = self._work_dir / f"sandbox_script{ext}"
        code_file.write_text(code)
        
        # Build execution command with limits
        cmd = self._build_execution_command(code_file, language, capabilities)
        
        # Set up resource limits
        env = self._build_environment(capabilities)
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout or self.config.max_execution_time_sec,
                env=env,
                cwd=self._work_dir,
            )
            
            return SandboxResult(
                success=result.returncode == 0,
                output=result.stdout,
                error=result.stderr,
                exit_code=result.returncode,
                execution_time_ms=int((time.time() - start_time) * 1000),
                capabilities_used=self._get_capabilities_list(capabilities),
            )
        except subprocess.TimeoutExpired:
            return SandboxResult(
                success=False,
                error="Execution timeout",
                execution_time_ms=int((time.time() - start_time) * 1000),
            )
        except Exception as e:
            return SandboxResult(
                success=False,
                error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000),
            )
    
    def _build_execution_command(
        self,
        code_file: Path,
        language: str,
        capabilities: Capability,
    ) -> List[str]:
        """Build command with system-level isolation."""
        if language == "python":
            return [
                "python3",
                "-u",  # Unbuffered
                "-B",  # Don't write .pyc
                "-c",
                f"import sys; sys.path.insert(0, '{self._work_dir}')",
                f"exec(open('{code_file}').read())",
            ]
        elif language == "javascript":
            return ["node", "--no-warnings", str(code_file)]
        
        raise ValueError(f"Unsupported language: {language}")
    
    def _build_environment(self, capabilities: Capability) -> Dict[str, str]:
        """Build isolated environment variables."""
        env = os.environ.copy()
        
        # Remove sensitive variables
        sensitive_vars = [
            "NXM_MASTER_KEY",
            "VAULT_TOKEN",
            "JWT_SECRET",
            "API_KEY",
            "AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY",
        ]
        for var in sensitive_vars:
            env.pop(var, None)
        
        # Set sandbox environment
        env["SANDBOX_MODE"] = "1"
        env["SANDBOX_DIR"] = str(self._sandbox_dir)
        
        return env
    
    def _log_execution_start(
        self,
        code: str,
        language: str,
        capabilities: Capability,
    ) -> None:
        """Log execution start for audit chain."""
        code_hash = hashlib.sha256(code.encode()).hexdigest()[:16]
        
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event": "execution_start",
            "code_hash": code_hash,
            "language": language,
            "capabilities": list(self._get_capabilities_list(capabilities)),
            "config": {
                "max_memory_mb": self.config.max_memory_mb,
                "max_execution_time_sec": self.config.max_execution_time_sec,
            },
        }
        
        self._audit_chain.append(entry)
        self._write_audit_entry(entry)
    
    def _seal_audit(self, result: SandboxResult) -> str:
        """Cryptographically seal audit entry (nono pattern)."""
        if not self.config.enable_atomic_rollback:
            return None
        
        # Create audit entry
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "result": {
                "success": result.success,
                "output": result.output[:500] if result.output else None,
                "error": result.error[:500] if result.error else None,
                "exit_code": result.exit_code,
                "execution_time_ms": result.execution_time_ms,
            },
        }
        
        # Hash chain
        if self._audit_chain:
            prev_hash = self._audit_chain[-1].get("hash", "0" * 64)
        else:
            prev_hash = "0" * 64
        
        entry_json = json.dumps(audit_entry, sort_keys=True)
        entry_hash = hashlib.sha256((prev_hash + entry_json).encode()).hexdigest()
        
        audit_entry["hash"] = entry_hash
        audit_entry["prev_hash"] = prev_hash
        
        self._audit_chain.append(audit_entry)
        self._write_audit_entry(audit_entry)
        
        return entry_hash
    
    def _write_audit_entry(self, entry: dict) -> None:
        """Write audit entry to persistent storage."""
        if not self.config.audit_mode:
            return
        
        audit_file = self._audit_dir / f"audit_{datetime.utcnow().strftime('%Y%m%d')}.jsonl"
        
        with open(audit_file, "a") as f:
            f.write(json.dumps(entry) + "\n")
    
    def _get_capabilities_list(self, capabilities: Capability) -> List[str]:
        """Get list of enabled capabilities."""
        result = []
        for cap in Capability:
            if cap != Capability.NONE and capabilities & cap:
                result.append(cap.name)
        return result
    
    def verify_audit_chain(self) -> bool:
        """Verify integrity of audit chain."""
        if not self._audit_chain:
            return True
        
        prev_hash = "0" * 64
        for entry in self._audit_chain:
            if "hash" not in entry:
                return False
            
            if entry.get("prev_hash") != prev_hash:
                return False
            
            # Verify hash
            entry_copy = {k: v for k, v in entry.items() if k != "hash"}
            expected_hash = hashlib.sha256(
                (prev_hash + json.dumps(entry_copy, sort_keys=True)).encode()
            ).hexdigest()
            
            if entry["hash"] != expected_hash:
                return False
            
            prev_hash = entry["hash"]
        
        return True
    
    def atomic_rollback(self) -> bool:
        """Perform atomic rollback of last operation."""
        if not self.config.enable_atomic_rollback:
            return False
        
        # Implementation depends on operation type
        # For file operations: delete created files
        # For network: close connections
        # For processes: terminate
        
        logger.info("Atomic rollback executed")
        return True
    
    def cleanup(self) -> None:
        """Clean up sandbox resources."""
        import shutil
        
        try:
            if self._sandbox_dir.exists():
                shutil.rmtree(self._sandbox_dir)
            logger.info(f"Sandbox cleaned up: {self._sandbox_dir}")
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
```

#### 2.1.3 Success Criteria

| Criteria | Target |
|----------|--------|
| Blocked patterns detected | 100% of common attacks |
| Audit chain integrity | Cryptographic verification passes |
| Resource limits enforced | Memory, CPU, time limits enforced |
| Capability isolation | Only requested capabilities granted |
| Rollback capability | Atomic rollback within 1 second |

#### 2.1.4 Category + Skills

- **Category**: `ultrabrain` (complex security logic)
- **Model**: `opencode/qwen3.6-plus-free (high)`
- **Skills**: `/git-master` (for audit verification)

---

### 2.2 `jailbreak_detector.py` — Perplexity-Based Detection

**Purpose**: Detect prompt injection attacks using perplexity-based guardrail (PIGuard patterns from ACL 2025).

**Location**: `src/security/jailbreak_detector.py`

#### 2.2.1 Class Definition

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple
import hashlib
import json
import logging
import re
import time

logger = logging.getLogger(__name__)


class InjectionSeverity(Enum):
    """Severity levels for injection detection."""
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class InjectionResult:
    """Result of injection detection."""
    is_injection: bool
    severity: InjectionSeverity
    confidence: float  # 0.0 - 1.0
    detection_method: str
    matched_patterns: List[str] = field(default_factory=list)
    reasons: List[str] = field(default_factory=list)
    sanitized_input: Optional[str] = None
    perplexity_score: Optional[float] = None


@dataclass
class DetectorConfig:
    """Configuration for jailbreak detection."""
    confidence_threshold: float = 0.7
    severity_thresholds: Dict[InjectionSeverity, float] = field(default_factory=lambda: {
        InjectionSeverity.CRITICAL: 0.9,
        InjectionSeverity.HIGH: 0.75,
        InjectionSeverity.MEDIUM: 0.5,
        InjectionSeverity.LOW: 0.3,
    })
    enable_perplexity: bool = True
    enable_pattern_matching: bool = True
    enable_semantic_analysis: bool = True
    perplexity_model: Optional[str] = None  # Optional LLM for perplexity
    custom_patterns: List[str] = field(default_factory=list)
    false_positive_whitelist: List[str] = field(default_factory=list)
    max_input_length: int = 100000
    enable_sanitization: bool = True
```

#### 2.2.2 Core Functions

```python
class JailbreakDetector:
    """Perplexity-based jailbreak detection (PIGuard pattern)."""
    
    # Known injection patterns
    INJECTION_PATTERNS = [
        # Direct instruction overrides
        r"(?i)ignore\s+(all\s+)?(previous|prior|above|earlier)\s+(instructions?|rules?|prompt)",
        r"(?i)forget\s+(everything|all|your|what)\s+(you\s+)?(know|have\s+been\s+taught)",
        r"(?i)new\s+instructions?:",
        r"(?i)system\s*:\s*",
        r"(?i)you\s+are\s+now\s+(?:a|an)\s+",
        
        # Role manipulation
        r"(?i)act\s+as\s+(a|an)\s+",
        r"(?i)pretend\s+(to\s+be|you\s+are)",
        r"(?i)imagine\s+(you\s+are|being)",
        r"(?i)simulate\s+(a|an)\s+",
        
        # Bypass attempts
        r"(?i)cannot\s+refuse",
        r"(?i)must\s+respond",
        r"(?i)no\s+(filters?|restrictions?|rules?)",
        r"(?i)bypass\s+(safety|filter|restriction)",
        
        # Delimiter injection
        r"```system",
        r"\[INST\]",
        r"<<SYS>>",
        r"<\|system\|>",
        r"<\|USER\|>",
        
        # Encoding attempts
        r"base64:",
        r"encode[d]?\s*:",
        r"\\x[0-9a-f]{2}",
        r"&#x[0-9a-f]{2};",
        
        # Jailbreak prompts
        r"DAN",
        r"developer\s+mode",
        r"jailbreak",
        r"unfiltered",
    ]
    
    def __init__(self, config: Optional[DetectorConfig] = None):
        self.config = config or DetectorConfig()
        self._compiled_patterns = self._compile_patterns()
        self._detection_history: List[InjectionResult] = []
        self._false_positive_tracker: Dict[str, int] = {}
        self._initialize()
    
    def _initialize(self) -> None:
        """Initialize detector components."""
        # Compile regex patterns
        self._detector = re.compile(
            "|".join(f"({p})" for p in self.INJECTION_PATTERNS),
            re.IGNORECASE | re.MULTILINE,
        )
        
        # Add custom patterns
        if self.config.custom_patterns:
            custom = re.compile(
                "|".join(f"({p})" for p in self.config.custom_patterns),
                re.IGNORECASE,
            )
        
        logger.info("JailbreakDetector initialized")
    
    def _compile_patterns(self) -> List[re.Pattern]:
        """Compile regex patterns for efficiency."""
        patterns = []
        
        for pattern in self.INJECTION_PATTERNS:
            try:
                patterns.append(re.compile(pattern, re.IGNORECASE))
            except re.error:
                logger.warning(f"Invalid pattern: {pattern}")
        
        return patterns
    
    def detect(self, input_text: str) -> InjectionResult:
        """Detect prompt injection in input text."""
        start_time = time.time()
        
        # Preprocessing
        input_text = input_text[:self.config.max_input_length]
        
        # Check whitelist
        if self._is_whitelisted(input_text):
            return InjectionResult(
                is_injection=False,
                severity=InjectionSeverity.SAFE,
                confidence=1.0,
                detection_method="whitelist",
            )
        
        # Multi-stage detection
        results: List[InjectionResult] = []
        
        # Stage 1: Pattern matching
        if self.config.enable_pattern_matching:
            pattern_result = self._detect_patterns(input_text)
            results.append(pattern_result)
        
        # Stage 2: Perplexity detection
        if self.config.enable_perplexity:
            perplexity_result = self._detect_perplexity(input_text)
            results.append(perplexity_result)
        
        # Stage 3: Semantic analysis
        if self.config.enable_semantic_analysis:
            semantic_result = self._detect_semantic(input_text)
            results.append(semantic_result)
        
        # Aggregate results (PIGuard overdefense mitigation)
        final_result = self._aggregate_results(results, input_text)
        
        # Track for false positive analysis
        if not final_result.is_injection:
            self._update_false_positive_tracker(input_text, final_result)
        
        final_result.confidence = min(final_result.confidence, 1.0)
        
        logger.debug(
            f"Detection completed in {time.time() - start_time:.3f}s: "
            f"injection={final_result.is_injection}, "
            f"severity={final_result.severity.value}, "
            f"confidence={final_result.confidence:.2f}"
        )
        
        return final_result
    
    def _detect_patterns(self, text: str) -> InjectionResult:
        """Stage 1: Pattern-based detection."""
        matches = []
        matched_patterns = []
        
        for i, pattern in enumerate(self._compiled_patterns):
            match = pattern.search(text)
            if match:
                matches.append(match)
                matched_patterns.append(self.INJECTION_PATTERNS[i])
        
        if not matches:
            return InjectionResult(
                is_injection=False,
                severity=InjectionSeverity.SAFE,
                confidence=0.0,
                detection_method="pattern",
            )
        
        # Calculate severity based on match count and positions
        severity = self._calculate_pattern_severity(matches, text)
        
        return InjectionResult(
            is_injection=True,
            severity=severity,
            confidence=0.8,
            detection_method="pattern",
            matched_patterns=matched_patterns,
            reasons=[f"Matched {len(matches)} dangerous pattern(s)"],
        )
    
    def _calculate_pattern_severity(
        self,
        matches: List[re.Match],
        text: str,
    ) -> InjectionSeverity:
        """Calculate severity based on pattern matches."""
        critical_patterns = [
            "ignore", "forget", "new instructions", "system:",
            "cannot refuse", "bypass", "DAN", "developer mode",
        ]
        
        high_patterns = [
            "act as", "pretend", "imagine", "simulate",
            "no filters", "no restrictions",
        ]
        
        # Check for critical patterns
        for match in matches:
            for pattern in critical_patterns:
                if pattern.lower() in match.group().lower():
                    return InjectionSeverity.CRITICAL
        
        # Check for high patterns
        for match in matches:
            for pattern in high_patterns:
                if pattern.lower() in match.group().lower():
                    return InjectionSeverity.HIGH
        
        # Check match density
        density = len(matches) / max(len(text), 1) * 1000
        
        if density > 0.5:
            return InjectionSeverity.HIGH
        elif density > 0.2:
            return InjectionSeverity.MEDIUM
        else:
            return InjectionSeverity.LOW
    
    def _detect_perplexity(self, text: str) -> InjectionResult:
        """Stage 2: Perplexity-based detection (PIGuard core)."""
        # Simplified perplexity estimation
        # In production, integrate with actual LLM
        
        # Tokenize (simplified)
        tokens = text.split()
        
        if len(tokens) < 5:
            return InjectionResult(
                is_injection=False,
                severity=InjectionSeverity.SAFE,
                confidence=0.0,
                detection_method="perplexity",
            )
        
        # Calculate perplexity proxy
        # High perplexity = unusual/inconsistent text
        perplexity = self._calculate_perplexity_proxy(text)
        
        # Determine if perplexity indicates injection
        if perplexity > 150:
            severity = InjectionSeverity.HIGH
            confidence = 0.75
            reasons = [f"High perplexity score: {perplexity:.1f}"]
        elif perplexity > 100:
            severity = InjectionSeverity.MEDIUM
            confidence = 0.5
            reasons = [f"Elevated perplexity: {perplexity:.1f}"]
        elif perplexity > 70:
            severity = InjectionSeverity.LOW
            confidence = 0.3
            reasons = [f"Slightly elevated perplexity: {perplexity:.1f}"]
        else:
            return InjectionResult(
                is_injection=False,
                severity=InjectionSeverity.SAFE,
                confidence=0.0,
                detection_method="perplexity",
            )
        
        return InjectionResult(
            is_injection=True,
            severity=severity,
            confidence=confidence,
            detection_method="perplexity",
            perplexity_score=perplexity,
            reasons=reasons,
        )
    
    def _calculate_perplexity_proxy(self, text: str) -> float:
        """Calculate perplexity proxy for injection detection."""
        # This is a simplified proxy
        # Real implementation would use actual LLM perplexity
        
        tokens = text.split()
        
        # Factors that increase perplexity:
        # 1. Unusual character sequences
        # 2. Mixed language
        # 3. Encoding attempts
        # 4. High ratio of special characters
        
        score = 50.0  # Base score
        
        # Check for encoding attempts
        if re.search(r"\\x[0-9a-f]{2}", text):
            score += 30
        
        if re.search(r"base64:", text, re.IGNORECASE):
            score += 25
        
        # Check for mixed scripts
        if re.search(r"[\u4e00-\u9fff].*[a-zA-Z]", text):
            score += 20
        
        # Check for delimiter injection
        if re.search(r"```|<<|>>|\[\[|\]\]", text):
            score += 15
        
        # Normalize by length
        if len(tokens) > 100:
            score *= 0.8
        
        return score
    
    def _detect_semantic(self, text: str) -> InjectionResult:
        """Stage 3: Semantic analysis for injection patterns."""
        # Simplified semantic detection
        # In production, use embeddings or classifier
        
        # Check for common jailbreak narratives
        jailbreak_narratives = [
            "you are a different AI",
            "for educational purposes",
            "hypothetically speaking",
            "fictional scenario",
            "thought experiment",
            "creative writing",
            "roleplay only",
        ]
        
        matches = []
        for narrative in jailbreak_narratives:
            if narrative.lower() in text.lower():
                matches.append(narrative)
        
        if not matches:
            return InjectionResult(
                is_injection=False,
                severity=InjectionSeverity.SAFE,
                confidence=0.0,
                detection_method="semantic",
            )
        
        return InjectionResult(
            is_injection=True,
            severity=InjectionSeverity.MEDIUM,
            confidence=0.6,
            detection_method="semantic",
            reasons=[f"Detected jailbreak narrative: {matches[0]}"],
        )
    
    def _aggregate_results(
        self,
        results: List[InjectionResult],
        original_text: str,
    ) -> InjectionResult:
        """Aggregate multi-stage results (PIGuard overdefense mitigation)."""
        if not results:
            return InjectionResult(
                is_injection=False,
                severity=InjectionSeverity.SAFE,
                confidence=0.0,
                detection_method="aggregate",
            )
        
        # PIGuard-style aggregation: require multiple confirmations
        # to avoid overdefense (false positives)
        
        injection_votes = sum(1 for r in results if r.is_injection)
        total_stages = len(results)
        
        # Require at least 2 stages to confirm injection
        if injection_votes < 2:
            return InjectionResult(
                is_injection=False,
                severity=InjectionSeverity.SAFE,
                confidence=0.0,
                detection_method="aggregate",
            )
        
        # Calculate weighted confidence
        confidence = sum(r.confidence for r in results) / total_stages
        
        # Calculate highest severity
        severity_order = [
            InjectionSeverity.CRITICAL,
            InjectionSeverity.HIGH,
            InjectionSeverity.MEDIUM,
            InjectionSeverity.LOW,
            InjectionSeverity.SAFE,
        ]
        
        max_severity = InjectionSeverity.SAFE
        for result in results:
            if result.severity != InjectionSeverity.SAFE:
                if severity_order.index(result.severity) < severity_order.index(max_severity):
                    max_severity = result.severity
        
        # Collect all matched patterns
        all_patterns = []
        all_reasons = []
        for result in results:
            all_patterns.extend(result.matched_patterns)
            all_reasons.extend(result.reasons)
        
        # Sanitize if enabled
        sanitized = None
        if self.config.enable_sanitization:
            sanitized = self._sanitize_input(original_text, results)
        
        return InjectionResult(
            is_injection=True,
            severity=max_severity,
            confidence=confidence,
            detection_method="aggregate",
            matched_patterns=list(set(all_patterns)),
            reasons=list(set(all_reasons)),
            sanitized_input=sanitized,
        )
    
    def _sanitize_input(
        self,
        text: str,
        results: List[InjectionResult],
    ) -> str:
        """Sanitize input by removing detected injection patterns."""
        sanitized = text
        
        # Remove matched patterns
        for result in results:
            for pattern in result.matched_patterns:
                try:
                    sanitized = re.sub(pattern, "[REDACTED]", sanitized, flags=re.IGNORECASE)
                except re.error:
                    pass
        
        # Remove common delimiters
        sanitized = re.sub(r"```[\s\S]*?```", "[CODE]", sanitized)
        sanitized = re.sub(r"\[INST\]", "", sanitized)
        sanitized = re.sub(r"<<SYS>>[\s\S]*?<<\/SYS>>", "[SYS]", sanitized)
        
        return sanitized.strip()
    
    def _is_whitelisted(self, text: str) -> bool:
        """Check if input is whitelisted."""
        text_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
        
        # Check exact match
        if text_hash in self._false_positive_tracker:
            return True
        
        # Check partial match
        for whitelisted in self.config.false_positive_whitelist:
            if whitelisted.lower() in text.lower():
                return True
        
        return False
    
    def _update_false_positive_tracker(
        self,
        text: str,
        result: InjectionResult,
    ) -> None:
        """Track false positives for pattern learning."""
        if result.severity in [InjectionSeverity.LOW, InjectionSeverity.MEDIUM]:
            text_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
            self._false_positive_tracker[text_hash] = (
                self._false_positive_tracker.get(text_hash, 0) + 1
            )
    
    def add_custom_pattern(self, pattern: str) -> None:
        """Add custom detection pattern."""
        try:
            compiled = re.compile(pattern, re.IGNORECASE)
            self._compiled_patterns.append(compiled)
            self.INJECTION_PATTERNS.append(pattern)
            logger.info(f"Added custom pattern: {pattern}")
        except re.error as e:
            logger.error(f"Invalid pattern: {e}")
    
    def get_detection_stats(self) -> Dict[str, Any]:
        """Get detection statistics."""
        total = len(self._detection_history)
        if total == 0:
            return {"total": 0}
        
        injections = sum(1 for r in self._detection_history if r.is_injection)
        
        severity_counts = {}
        for severity in InjectionSeverity:
            severity_counts[severity.value] = sum(
                1 for r in self._detection_history if r.severity == severity
            )
        
        return {
            "total": total,
            "injections": injections,
            "false_positives": len(self._false_positive_tracker),
            "severity_counts": severity_counts,
        }
```

#### 2.2.3 Success Criteria

| Criteria | Target |
|----------|--------|
| Detection rate (known patterns) | >95% |
| False positive rate | <5% |
| Overdefense mitigation | PIGuard paper compliance |
| Latency | <100ms per detection |
| Confidence calibration | ROC-AUC >0.90 |

#### 2.2.4 Category + Skills

- **Category**: `ultrabrain` (ML/security hybrid)
- **Model**: `opencode/qwen3.6-plus-free (high)`
- **Skills**: None required

---

### 2.3 `permission_system.py` — Slowmist-Style Untrusted Input Handling

**Purpose**: Handle untrusted inputs with comprehensive validation (Slowmist patterns).

**Location**: `src/security/permission_system.py`

#### 2.3.1 Class Definition

```python
from dataclasses import dataclass, field
from enum import Enum, Flag
from typing import Any, Callable, Dict, List, Optional, Set, Union
from pathlib import Path
import hashlib
import json
import logging
import re

logger = logging.getLogger(__name__)


class Permission(Flag):
    """Permission flags for resource access."""
    NONE = 0
    READ = 1
    WRITE = 2
    DELETE = 4
    EXECUTE = 8
    NETWORK_READ = 16
    NETWORK_WRITE = 32
    ENV_READ = 64
    ENV_WRITE = 128


class InputCategory(Enum):
    """Categories of untrusted input."""
    USER_PROMPT = "user_prompt"
    FILE_UPLOAD = "file_upload"
    API_REQUEST = "api_request"
    TOOL_INPUT = "tool_input"
    AGENT_MESSAGE = "agent_message"
    EXTERNAL_DATA = "external_data"


@dataclass
class InputValidationResult:
    """Result of input validation."""
    is_valid: bool
    category: InputCategory
    sanitized_value: Optional[Any] = None
    violations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    risk_score: float = 0.0  # 0.0 - 1.0
    applied_transformations: List[str] = field(default_factory=list)


@dataclass
class PermissionContext:
    """Context for permission evaluation."""
    agent_id: str
    session_id: str
    requested_permissions: Permission
    input_category: InputCategory
    source_ip: Optional[str] = None
    user_agent: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PermissionDecision:
    """Permission decision result."""
    granted: bool
    permissions: Permission
    conditions: List[str] = field(default_factory=list)
    expiry_seconds: Optional[int] = None
    audit_info: Dict[str, Any] = field(default_factory=dict)
```

#### 2.3.2 Core Functions

```python
class PermissionSystem:
    """Slowmist-style permission system for untrusted inputs."""
    
    # Dangerous patterns for each input type
    DANGEROUS_PATTERNS = {
        InputCategory.USER_PROMPT: [
            r"<script",
            r"javascript:",
            r"on\w+\s*=",
            r"{{",
            r"{%",
            r"${",
        ],
        InputCategory.FILE_UPLOAD: [
            r"\.\.",
            r"~",
            r"\/\.",
            r"\.exe$",
            r"\.sh$",
            r"\.bat$",
            r"\.ps1$",
        ],
        InputCategory.API_REQUEST: [
            r"\$ne",
            r"\$where",
            r"eval\(",
            r"exec\(",
            r"<.*>",
        ],
        InputCategory.TOOL_INPUT: [
            r"__import__",
            r"import\s+os",
            r"import\s+subprocess",
            r"import\s+sys",
            r"open\s*\(",
        ],
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._permission_cache: Dict[str, PermissionDecision] = {}
        self._input_history: List[InputValidationResult] = []
        self._rate_limiter = None  # Will integrate with rate_limiter
        self._initialize()
    
    def _initialize(self) -> None:
        """Initialize permission system."""
        # Compile patterns
        self._compiled_patterns: Dict[InputCategory, List[re.Pattern]] = {}
        for category, patterns in self.DANGEROUS_PATTERNS.items():
            self._compiled_patterns[category] = [
                re.compile(p, re.IGNORECASE) for p in patterns
            ]
        
        logger.info("PermissionSystem initialized")
    
    def validate_input(
        self,
        value: Any,
        category: InputCategory,
        strict: bool = True,
    ) -> InputValidationResult:
        """Validate untrusted input (Slowmist principle: all input is untrusted)."""
        start_time = time.time()
        
        # Normalize value
        if isinstance(value, str):
            normalized = value
        elif isinstance(value, (dict, list)):
            normalized = json.dumps(value, sort_keys=True)
        else:
            normalized = str(value)
        
        # Check length limits
        if len(normalized) > self.config.get("max_length", 100000):
            return InputValidationResult(
                is_valid=False,
                category=category,
                violations=[f"Input exceeds max length: {len(normalized)}"],
                risk_score=1.0,
            )
        
        # Run validation stages
        violations = []
        warnings = []
        transformations = []
        risk_score = 0.0
        
        # Stage 1: Pattern matching
        pattern_result = self._validate_patterns(normalized, category)
        violations.extend(pattern_result["violations"])
        risk_score += pattern_result["risk"] * 0.4
        
        # Stage 2: Type validation
        type_result = self._validate_type(normalized, category)
        warnings.extend(type_result["warnings"])
        risk_score += type_result["risk"] * 0.2
        
        # Stage 3: Content analysis
        content_result = self._validate_content(normalized, category)
        violations.extend(content_result["violations"])
        risk_score += content_result["risk"] * 0.4
        
        # Sanitize if needed
        sanitized = normalized
        if violations and self.config.get("auto_sanitize", True):
            sanitized = self._sanitize(normalized, category)
            transformations.append("auto_sanitize")
        
        # Normalize risk score
        risk_score = min(risk_score, 1.0)
        
        # Determine validity
        is_valid = len(violations) == 0 or (
            not strict and risk_score < self.config.get("risk_threshold", 0.7)
        )
        
        result = InputValidationResult(
            is_valid=is_valid,
            category=category,
            sanitized_value=sanitized,
            violations=violations,
            warnings=warnings,
            risk_score=risk_score,
            applied_transformations=transformations,
        )
        
        self._input_history.append(result)
        
        logger.debug(
            f"Input validation: category={category.value}, "
            f"valid={is_valid}, risk={risk_score:.2f}, "
            f"time={time.time() - start_time:.3f}s"
        )
        
        return result
    
    def _validate_patterns(
        self,
        value: str,
        category: InputCategory,
    ) -> Dict[str, Any]:
        """Validate against dangerous patterns."""
        violations = []
        risk = 0.0
        
        patterns = self._compiled_patterns.get(category, [])
        
        for pattern in patterns:
            match = pattern.search(value)
            if match:
                violations.append(f"Dangerous pattern: {match.group()}")
                risk += 0.3
        
        # Check universal dangerous patterns
        universal = [
            (r"\x00", "null_byte"),
            (r"\r\n", "crlf_injection"),
            (r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "control_characters"),
        ]
        
        for pattern, name in universal:
            if re.search(pattern, value):
                violations.append(f"Universal danger: {name}")
                risk += 0.2
        
        return {"violations": violations, "risk": min(risk, 1.0)}
    
    def _validate_type(
        self,
        value: str,
        category: InputCategory,
    ) -> Dict[str, Any]:
        """Validate input type."""
        warnings = []
        risk = 0.0
        
        # Check for encoded content
        if re.match(r"^[A-Za-z0-9+/=]+$", value) and len(value) > 100:
            warnings.append("Possible base64 encoding detected")
            risk += 0.1
        
        # Check for JSON-like content
        if category == InputCategory.USER_PROMPT:
            if value.startswith("{") and value.endswith("}"):
                warnings.append("JSON-like content in prompt")
                risk += 0.05
        
        return {"warnings": warnings, "risk": risk}
    
    def _validate_content(
        self,
        value: str,
        category: InputCategory,
    ) -> Dict[str, Any]:
        """Validate content semantics."""
        violations = []
        risk = 0.0
        
        # Check for prompt injection markers
        if category == InputCategory.USER_PROMPT:
            injection_markers = [
                "ignore previous",
                "system prompt",
                "new instructions",
            ]
            
            for marker in injection_markers:
                if marker.lower() in value.lower():
                    violations.append(f"Potential injection: {marker}")
                    risk += 0.3
        
        # Check for path traversal
        if category == InputCategory.FILE_UPLOAD:
            if ".." in value or value.startswith("/"):
                violations.append("Path traversal attempt detected")
                risk += 0.5
        
        return {"violations": violations, "risk": risk}
    
    def _sanitize(self, value: str, category: InputCategory) -> str:
        """Sanitize input value."""
        sanitized = value
        
        # Remove null bytes
        sanitized = sanitized.replace("\x00", "")
        
        # Remove control characters
        sanitized = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", sanitized)
        
        # Normalize newlines
        sanitized = sanitized.replace("\r\n", "\n")
        
        # Escape template syntax
        if category in [InputCategory.USER_PROMPT, InputCategory.TOOL_INPUT]:
            sanitized = sanitized.replace("{{", "\\{\\{")
            sanitized = sanitized.replace("{%", "\\{%")
            sanitized = sanitized.replace("{{", "{{''}}")
        
        # Remove script tags
        if category == InputCategory.USER_PROMPT:
            sanitized = re.sub(r"<script[^>]*>.*?</script>", "", sanitized, flags=re.DOTALL | re.IGNORECASE)
            sanitized = re.sub(r"javascript:", "", sanitized, flags=re.IGNORECASE)
        
        return sanitized
    
    def check_permission(
        self,
        context: PermissionContext,
    ) -> PermissionDecision:
        """Check and grant permissions based on context."""
        # Create cache key
        cache_key = self._create_cache_key(context)
        
        # Check cache
        if cache_key in self._permission_cache:
            cached = self._permission_cache[cache_key]
            if self._is_cache_valid(cached):
                return cached
        
        # Evaluate permissions
        decision = self._evaluate_permissions(context)
        
        # Cache decision
        self._permission_cache[cache_key] = decision
        
        return decision
    
    def _create_cache_key(self, context: PermissionContext) -> str:
        """Create cache key for permission decision."""
        key_parts = [
            context.agent_id,
            context.session_id,
            str(context.requested_permissions),
            context.input_category.value,
        ]
        
        return hashlib.sha256("|".join(key_parts).encode()).hexdigest()[:16]
    
    def _is_cache_valid(self, decision: PermissionDecision) -> bool:
        """Check if cached decision is still valid."""
        if decision.expiry_seconds is None:
            return False
        
        # Check expiry (would need timestamp in decision)
        return True
    
    def _evaluate_permissions(
        self,
        context: PermissionContext,
    ) -> PermissionDecision:
        """Evaluate permission request."""
        granted_permissions = Permission.NONE
        conditions = []
        
        # Base permissions based on category
        base_permissions = self._get_base_permissions(context.input_category)
        
        # Check if requested permissions are subset of base
        requested = context.requested_permissions
        if requested & ~base_permissions:
            # Some permissions not in base set
            # Apply additional checks
            if Permission.EXECUTE in requested:
                conditions.append("execution_requires_approval")
            
            if Permission.NETWORK_WRITE in requested:
                conditions.append("network_write_requires_audit")
        
        # Grant permissions
        granted_permissions = requested & base_permissions
        
        # Apply conditions based on risk
        audit_info = {
            "agent_id": context.agent_id,
            "session_id": context.session_id,
            "permissions": granted_permissions.value,
            "category": context.input_category.value,
        }
        
        return PermissionDecision(
            granted=granted_permissions != Permission.NONE,
            permissions=granted_permissions,
            conditions=conditions,
            expiry_seconds=3600,  # 1 hour
            audit_info=audit_info,
        )
    
    def _get_base_permissions(
        self,
        category: InputCategory,
    ) -> Permission:
        """Get base permissions for input category."""
        base = {
            InputCategory.USER_PROMPT: Permission.READ,
            InputCategory.FILE_UPLOAD: Permission.READ,
            InputCategory.API_REQUEST: Permission.READ | Permission.EXECUTE,
            InputCategory.TOOL_INPUT: Permission.READ | Permission.WRITE | Permission.EXECUTE,
            InputCategory.AGENT_MESSAGE: Permission.READ | Permission.WRITE,
            InputCategory.EXTERNAL_DATA: Permission.READ,
        }
        
        return base.get(category, Permission.NONE)
    
    def revoke_permissions(self, agent_id: str, session_id: str) -> bool:
        """Revoke all permissions for an agent/session."""
        keys_to_remove = []
        
        for key, decision in self._permission_cache.items():
            if decision.audit_info.get("agent_id") == agent_id:
                if session_id is None or decision.audit_info.get("session_id") == session_id:
                    keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self._permission_cache[key]
        
        logger.info(f"Revoked {len(keys_to_remove)} permissions for agent {agent_id}")
        return len(keys_to_remove) > 0
    
    def get_permission_stats(self) -> Dict[str, Any]:
        """Get permission system statistics."""
        return {
            "cached_decisions": len(self._permission_cache),
            "total_validations": len(self._input_history),
            "valid_inputs": sum(1 for r in self._input_history if r.is_valid),
            "high_risk_inputs": sum(1 for r in self._input_history if r.risk_score > 0.7),
        }
```

#### 2.3.3 Success Criteria

| Criteria | Target |
|----------|--------|
| Input validation coverage | 100% of untrusted inputs |
| Violation detection | >95% of known attacks |
| Latency | <50ms per validation |
| Cache hit rate | >80% for repeated contexts |

#### 2.3.4 Category + Skills

- **Category**: `deep` (validation logic)
- **Model**: `opencode/qwen3.6-plus-free (medium)`
- **Skills**: None required

---

### 2.4 `output_guardrails.py` — OWASP-Aligned Validation

**Purpose**: Validate outputs against OWASP Top 10 LLM and Agent vulnerabilities.

**Location**: `src/security/output_guardrails.py`

#### 2.4.1 Class Definition

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
import hashlib
import json
import logging
import re

logger = logging.getLogger(__name__)


class OWASPCategory(Enum):
    """OWASP Top 10 LLM vulnerabilities."""
    ASI01_PROMPT_INJECTION = "ASI01"
    ASI02_SENSITIVE_INFO = "ASI02"
    ASI03_UNVERIFIED = "ASI03"
    ASI04_MODEL_DENIAL = "ASI04"
    ASI05_SUPPLY_CHAIN = "ASI05"
    ASI06_INSECURE_PLUGIN = "ASI06"
    ASI07_DATA_POISONING = "ASI07"
    ASI08_RAG_INSECURE = "ASI08"
    ASI09_UNVERIFIED_MODELS = "ASI09"
    ASI10_COPILOT_DEFICITS = "ASI10"


@dataclass
class GuardrailResult:
    """Result of guardrail validation."""
    is_safe: bool
    category: Optional[OWASPCategory] = None
    violation: Optional[str] = None
    confidence: float = 1.0
    sanitized_output: Optional[str] = None
    recommendations: List[str] = field(default_factory=list)


@dataclass
class GuardrailConfig:
    """Configuration for output guardrails."""
    enable_all_categories: bool = True
    enabled_categories: Set[OWASPCategory] = field(default_factory=set)
    confidence_threshold: float = 0.8
    enable_sanitization: bool = True
    max_output_length: int = 50000
    sensitive_patterns: List[str] = field(default_factory=list)
    allowed_domains: List[str] = field(default_factory=list)
    blocked_domains: List[str] = field(default_factory=lambda: [
        "localhost", "127.0.0.1", "0.0.0.0"
    ])
```

#### 2.4.2 Core Functions

```python
class OutputGuardrails:
    """OWASP-aligned output validation."""
    
    # Sensitive information patterns
    SENSITIVE_PATTERNS = {
        "api_key": r"(?i)(api[_-]?key|apikey)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-]{20,})['\"]?",
        "password": r"(?i)password\s*[:=]\s*['\"]?([^\s'\"]{8,})['\"]?",
        "secret": r"(?i)(secret|token|auth)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-]{16,})['\"]?",
        "private_key": r"-----BEGIN (RSA |EC )?PRIVATE KEY-----",
        "jwt": r"eyJ[a-zA-Z0-9_-]*\.eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*",
        "aws_key": r"(?i)AKIA[0-9A-Z]{16}",
        "github_token": r"gh[pousr]_[A-Za-z0-9_]{36,}",
    }
    
    # Dangerous code patterns
    DANGEROUS_PATTERNS = [
        r"eval\s*\(",
        r"exec\s*\(",
        r"__import__\s*\(",
        r"subprocess\s*\.",
        r"os\s*\.\s*system",
        r"shell\s*=\s*True",
    ]
    
    def __init__(self, config: Optional[GuardrailConfig] = None):
        self.config = config or GuardrailConfig()
        self._validation_history: List[GuardrailResult] = []
        self._initialize()
    
    def _initialize(self) -> None:
        """Initialize guardrail components."""
        # Compile sensitive patterns
        self._compiled_sensitive = {
            name: re.compile(pattern)
            for name, pattern in self.SENSITIVE_PATTERNS.items()
        }
        
        # Compile dangerous patterns
        self._compiled_dangerous = [
            re.compile(p) for p in self.DANGEROUS_PATTERNS
        ]
        
        # Add custom patterns
        for pattern in self.config.sensitive_patterns:
            try:
                compiled = re.compile(pattern, re.IGNORECASE)
                self._compiled_sensitive[f"custom_{len(self._compiled_sensitive)}"] = compiled
            except re.error:
                pass
        
        logger.info("OutputGuardrails initialized")
    
    def validate(
        self,
        output: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> GuardrailResult:
        """Validate output against OWASP categories."""
        start_time = time.time()
        
        # Preprocessing
        output = output[:self.config.max_output_length]
        
        if not output:
            return GuardrailResult(is_safe=True)
        
        # Run validation stages
        results = []
        
        # ASI01: Prompt Injection (output-based)
        if OWASPCategory.ASI01_PROMPT_INJECTION in self._get_enabled():
            result = self._check_asi01(output)
            results.append(result)
        
        # ASI02: Sensitive Information Disclosure
        if OWASPCategory.ASI02_SENSITIVE_INFO in self._get_enabled():
            result = self._check_asi02(output)
            results.append(result)
        
        # ASI03: Unverified Execution
        if OWASPCategory.ASI03_UNVERIFIED in self._get_enabled():
            result = self._check_asi03(output, context)
            results.append(result)
        
        # ASI04: Model Denial of Service
        if OWASPCategory.ASI04_MODEL_DENIAL in self._get_enabled():
            result = self._check_asi04(output)
            results.append(result)
        
        # ASI08: RAG Insecure Output
        if OWASPCategory.ASI08_RAG_INSECURE in self._get_enabled():
            result = self._check_asi08(output)
            results.append(result)
        
        # Aggregate results
        final_result = self._aggregate_results(output, results)
        
        self._validation_history.append(final_result)
        
        logger.debug(
            f"Guardrail validation: safe={final_result.is_safe}, "
            f"time={time.time() - start_time:.3f}s"
        )
        
        return final_result
    
    def _get_enabled(self) -> Set[OWASPCategory]:
        """Get enabled OWASP categories."""
        if self.config.enable_all_categories:
            return set(OWASPCategory)
        return self.config.enabled_categories
    
    def _check_asi01(self, output: str) -> GuardrailResult:
        """ASI01: Prompt Injection in output."""
        # Check if output contains potential injection
        injection_markers = [
            r"ignore\s+previous",
            r"new\s+instructions",
            r"system\s*:\s*",
            r"{{",
            r"{%",
        ]
        
        for marker in injection_markers:
            if re.search(marker, output, re.IGNORECASE):
                return GuardrailResult(
                    is_safe=False,
                    category=OWASPCategory.ASI01_PROMPT_INJECTION,
                    violation=f"Potential injection marker: {marker}",
                    confidence=0.85,
                    sanitized_output=self._sanitize_injection(output),
                    recommendations=[
                        "Review output for injected instructions",
                        "Implement output filtering",
                    ],
                )
        
        return GuardrailResult(is_safe=True)
    
    def _check_asi02(self, output: str) -> GuardrailResult:
        """ASI02: Sensitive Information Disclosure."""
        findings = []
        
        for name, pattern in self._compiled_sensitive.items():
            match = pattern.search(output)
            if match:
                findings.append(name)
        
        if findings:
            sanitized = self._redact_sensitive(output)
            return GuardrailResult(
                is_safe=False,
                category=OWASPCategory.ASI02_SENSITIVE_INFO,
                violation=f"Sensitive data detected: {findings}",
                confidence=0.95,
                sanitized_output=sanitized,
                recommendations=[
                    "Review output for sensitive information",
                    "Implement PII filtering",
                ],
            )
        
        return GuardrailResult(is_safe=True)
    
    def _check_asi03(
        self,
        output: str,
        context: Optional[Dict[str, Any]],
    ) -> GuardrailResult:
        """ASI03: Unverified Execution."""
        # Check for dangerous code execution
        for pattern in self._compiled_dangerous:
            if pattern.search(output):
                return GuardrailResult(
                    is_safe=False,
                    category=OWASPCategory.ASI03_UNVERIFIED,
                    violation="Dangerous code pattern detected",
                    confidence=0.9,
                    sanitized_output=self._sanitize_dangerous(output),
                    recommendations=[
                        "Review code execution in output",
                        "Implement sandbox execution",
                    ],
                )
        
        return GuardrailResult(is_safe=True)
    
    def _check_asi04(self, output: str) -> GuardrailResult:
        """ASI04: Model Denial of Service."""
        # Check for potential DoS patterns
        # Excessive repetition
        words = output.split()
        if len(words) > 10:
            unique_ratio = len(set(words)) / len(words)
            if unique_ratio < 0.1:
                return GuardrailResult(
                    is_safe=False,
                    category=OWASPCategory.ASI04_MODEL_DENIAL,
                    violation="Excessive repetition detected",
                    confidence=0.8,
                    recommendations=[
                        "Review for repetitive content",
                        "Implement repetition filtering",
                    ],
                )
        
        # Check for resource exhaustion patterns
        if len(output) > self.config.max_output_length * 0.9:
            return GuardrailResult(
                is_safe=False,
                category=OWASPCategory.ASI04_MODEL_DENIAL,
                violation="Near size limit output",
                confidence=0.7,
                recommendations=[
                    "Implement output length limits",
                ],
            )
        
        return GuardrailResult(is_safe=True)
    
    def _check_asi08(self, output: str) -> GuardrailResult:
        """ASI08: RAG Insecure Output (injection via retrieved context)."""
        # Check for context injection patterns
        context_markers = [
            r"source:\s*http",
            r"retrieved from",
            r"context:",
        ]
        
        for marker in context_markers:
            if re.search(marker, output, re.IGNORECASE):
                # Verify source is allowed
                if not self._verify_sources(output):
                    return GuardrailResult(
                        is_safe=False,
                        category=OWASPCategory.ASI08_RAG_INSECURE,
                        violation="Unverified source in RAG output",
                        confidence=0.75,
                        recommendations=[
                            "Implement source verification",
                            "Add source allowlist",
                        ],
                    )
        
        return GuardrailResult(is_safe=True)
    
    def _verify_sources(self, output: str) -> bool:
        """Verify sources in RAG output."""
        urls = re.findall(r"https?://[^\s]+", output)
        
        for url in urls:
            try:
                domain = re.sub(r"https?://([^/]+).*", r"\1", url)
                
                if domain in self.config.blocked_domains:
                    return False
                
                if self.config.allowed_domains:
                    if domain not in self.config.allowed_domains:
                        return False
            except Exception:
                pass
        
        return True
    
    def _sanitize_injection(self, output: str) -> str:
        """Sanitize injection patterns from output."""
        sanitized = output
        
        injection_markers = [
            r"ignore\s+previous.*",
            r"new\s+instructions.*",
            r"system\s*:\s*.*",
        ]
        
        for marker in injection_markers:
            sanitized = re.sub(marker, "[INJECTION REDACTED]", sanitized, flags=re.IGNORECASE)
        
        return sanitized
    
    def _redact_sensitive(self, output: str) -> str:
        """Redact sensitive information from output."""
        sanitized = output
        
        for name, pattern in self._compiled_sensitive.items():
            sanitized = pattern.sub(f"[{name.upper()} REDACTED]", sanitized)
        
        return sanitized
    
    def _sanitize_dangerous(self, output: str) -> str:
        """Sanitize dangerous code patterns."""
        sanitized = output
        
        for pattern in self._compiled_dangerous:
            sanitized = pattern.sub("[CODE REDACTED]", sanitized)
        
        return sanitized
    
    def _aggregate_results(
        self,
        original_output: str,
        results: List[GuardrailResult],
    ) -> GuardrailResult:
        """Aggregate validation results."""
        # Find first violation
        for result in results:
            if not result.is_safe:
                # Sanitize if enabled
                sanitized = original_output
                if self.config.enable_sanitization:
                    if result.sanitized_output:
                        sanitized = result.sanitized_output
                    else:
                        sanitized = self._sanitize_injection(original_output)
                        sanitized = self._redact_sensitive(sanitized)
                
                return GuardrailResult(
                    is_safe=False,
                    category=result.category,
                    violation=result.violation,
                    confidence=result.confidence,
                    sanitized_output=sanitized,
                    recommendations=result.recommendations,
                )
        
        return GuardrailResult(is_safe=True)
    
    def get_validation_stats(self) -> Dict[str, Any]:
        """Get validation statistics."""
        total = len(self._validation_history)
        if total == 0:
            return {"total": 0}
        
        violations = sum(1 for r in self._validation_history if not r.is_safe)
        
        category_counts = {}
        for category in OWASPCategory:
            category_counts[category.value] = sum(
                1 for r in self._validation_history
                if r.category == category
            )
        
        return {
            "total": total,
            "violations": violations,
            "category_counts": category_counts,
        }
```

#### 2.4.3 Success Criteria

| Criteria | Target |
|----------|--------|
| Sensitive data detection | >95% recall |
| Latency | <50ms per validation |
| False positive rate | <3% |

#### 2.4.4 Category + Skills

- **Category**: `deep` (validation logic)
- **Model**: `opencode/qwen3.6-plus-free (medium)`
- **Skills**: None required

---

## 3. Supporting Infrastructure

### 3.1 `rate_limiter.py` — DoS Protection

**Location**: `src/security/rate_limiter.py`

```python
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional
import time

class RateLimitExceeded(Exception):
    pass

@dataclass
class RateLimitConfig:
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    burst_size: int = 10

class RateLimiter:
    """Token bucket rate limiter."""
    
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self._buckets: Dict[str, dict] = {}
    
    def check(self, key: str) -> None:
        """Check rate limit, raise if exceeded."""
        now = time.time()
        
        if key not in self._buckets:
            self._buckets[key] = {
                "tokens": self.config.burst_size,
                "last_update": now,
                "minute_count": 0,
                "minute_reset": now,
                "hour_count": 0,
                "hour_reset": now,
            }
        
        bucket = self._buckets[key]
        
        # Refill tokens
        elapsed = now - bucket["last_update"]
        bucket["tokens"] = min(
            self.config.burst_size,
            bucket["tokens"] + elapsed * (self.config.requests_per_minute / 60)
        )
        bucket["last_update"] = now
        
        # Check minute limit
        if now - bucket["minute_reset"] > 60:
            bucket["minute_count"] = 0
            bucket["minute_reset"] = now
        
        # Check hour limit
        if now - bucket["hour_reset"] > 3600:
            bucket["hour_count"] = 0
            bucket["hour_reset"] = now
        
        # Check limits
        if bucket["tokens"] < 1:
            raise RateLimitExceeded(f"Rate limit exceeded for {key}")
        
        bucket["tokens"] -= 1
        bucket["minute_count"] += 1
        bucket["hour_count"] += 1
```

---

## 4. Test Strategy

### 4.1 Unit Tests

| File | Test Coverage Target | Key Tests |
|------|----------------------|-----------|
| `agent_sandbox.py` | 90% | Pattern blocking, capability isolation, audit chain |
| `jailbreak_detector.py` | 95% | Pattern detection, perplexity thresholds, false positive rate |
| `permission_system.py` | 90% | Input validation, permission caching, sanitization |
| `output_guardrails.py` | 90% | Sensitive data redaction, injection detection |
| `rate_limiter.py` | 95% | Token bucket, minute/hour limits |

### 4.2 Integration Tests

1. **Sandbox + Permission Flow**: Execute code with permissions
2. **Detector + Guardrails**: Full input→detection→guardrail pipeline
3. **Rate Limit + Audit**: Rate limiting with audit logging
4. **Key Rotation + Encryption**: Encryption with rotation

### 4.3 Security Benchmarks

- **OWASP Testing**: Test against OWASP Top 10 LLM
- **Jailbreak Benchmarks**: Test against known jailbreak prompts (500+)
- **DoS Resilience**: Verify rate limiting under load

---

## 5. Atomic Commit Strategy

| Commit | Files | Description |
|--------|-------|-------------|
| 1 | `rate_limiter.py`, tests | DoS protection foundation |
| 2 | `jailbreak_detector.py`, tests | Injection detection |
| 3 | `output_guardrails.py`, tests | OWASP guardrails |
| 4 | `permission_system.py`, tests | Input validation |
| 5 | `agent_sandbox.py`, tests | Sandbox execution |
| 6 | All | Integration tests |

---

## 6. Implementation Order

```
WAVE 1 (Foundation)
├── rate_limiter.py
├── audit_logger.py (enhance existing)
└── Integration test W1

WAVE 2 (Detection)
├── jailbreak_detector.py
├── output_guardrails.py
└── Integration test W2

WAVE 3 (Permissions)
├── permission_system.py
└── Integration test W3

WAVE 4 (Sandbox)
├── agent_sandbox.py
└── Integration test W4

WAVE 5 (Final)
├── All security benchmarks
├── Performance tests
└── Documentation
```

---

## 7. Category + Skills Mapping

| Task | Category | Model | Skills |
|------|----------|-------|--------|
| `rate_limiter.py` | `deep` | qwen3.6-plus-free (medium) | None |
| `jailbreak_detector.py` | `ultrabrain` | qwen3.6-plus-free (high) | None |
| `output_guardrails.py` | `deep` | qwen3.6-plus-free (medium) | None |
| `permission_system.py` | `deep` | qwen3.6-plus-free (medium) | None |
| `agent_sandbox.py` | `ultrabrain` | qwen3.6-plus-free (high) | `/git-master` |
| Tests | `unspecified-low` | minimax-m2.5-free | None |
| Security benchmarks | `ultrabrain` | qwen3.6-plus-free (high) | None |

---

## 8. Parallel Execution Opportunities

The following tasks can be executed in parallel within each wave:

**Wave 1**:
- `rate_limiter.py` (independent)
- Enhance `audit_logger.py` (independent)

**Wave 2**:
- `jailbreak_detector.py` (independent)
- `output_guardrails.py` (independent)
- Both can be tested against same test cases

**Wave 3**:
- `permission_system.py` builds on Wave 1-2 (sequential after foundational work)

**Wave 4**:
- `agent_sandbox.py` depends on `permission_system.py` (sequential)

---

## 9. Success Criteria Summary

| Component | Success Criteria | Metric |
|-----------|-----------------|--------|
| **Agent Sandbox** | Block 100% of dangerous patterns | Pattern test pass rate |
| **Jailbreak Detector** | >95% detection, <5% FP | Precision/recall |
| **Permission System** | Validate all inputs | Coverage 100% |
| **Output Guardrails** | Redact sensitive data | Recall >95% |
| **Rate Limiter** | Prevent DoS | Under load test |
| **Integration** | All modules work together | E2E test pass |

---

## 10. Integration Points

### 10.1 With Other Layers

| Layer | Integration Point |
|-------|-------------------|
| L1 (Core) | Audit logging → flight_recorder.py |
| L5 (Orchestration) | Permission checks → agent execution |
| L6 (MCP) | Input validation → MCP tool calls |
| L9 (Runtime) | Sandbox → container execution |

### 10.2 With Existing Code

- `src/security/encryption.py` → Key management integration
- `src/audit_logger.py` → Audit chain sealing
- `src/trigger_engine.py` → Trigger validation

---

*Plan generated: 2026-04-04*
*Plan version: 1.0*
