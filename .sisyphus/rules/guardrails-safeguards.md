# Guardrails & Safeguards — Automation Safety System

## The Problem

With 41 automations running, we need:
1. Guardrails (what CAN'T happen)
2. Safeguards (what MUST be verified)
3. No-go zones (absolute prohibitions)
4. Confirmation prompts (for dangerous actions)
5. Hallucination prevention (double-check everything)

## The Solution: 5-Layer Safety System

```
┌─────────────────────────────────────────────────────────────┐
│                    5-LAYER SAFETY SYSTEM                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  LAYER 1: NO-GO ZONES (Absolute Prohibitions)              │
│  └─ Never delete .git, .env, credentials, configs          │
│                                                              │
│  LAYER 2: ROLE VERIFICATION (Check Before Act)              │
│  └─ Am I supposed to do this? Is this my job?              │
│                                                              │
│  LAYER 3: CONFIRMATION PROMPTS (Dangerous Actions)          │
│  └─ Ask user before deleting, overwriting, deploying       │
│                                                              │
│  LAYER 4: HALLUCINATION CHECK (Double-Verify)              │
│  └─ Does this file exist? Is this path valid?              │
│                                                              │
│  LAYER 5: AUDIT LOG (Track Everything)                      │
│  └─ Log all actions for review and rollback                │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Layer 1: No-Go Zones (Absolute Prohibitions)

### NEVER DELETE
- `.git/` directory
- `.env` files
- `credentials.json`
- `*.key`, `*.pem` files
- `package-lock.json`, `yarn.lock`
- Database files (`*.db`, `*.sqlite`)
- Config files (`opencode.json`, `oh-my-opencode.json`)

### NEVER OVERWRITE
- Production configs
- Database schemas
- User data
- API keys
- Certificates

### NEVER EXECUTE WITHOUT CONFIRMATION
- `rm -rf` (recursive delete)
- `git push --force`
- `docker rm` (remove containers)
- `DROP TABLE` (database)
- `format` (disk format)
- `shutdown` / `restart`

```python
NO_GO_ZONES = {
    "never_delete": [
        ".git", ".env", "credentials.json",
        "*.key", "*.pem", "package-lock.json",
        "*.db", "*.sqlite", "opencode.json"
    ],
    "never_overwrite": [
        "production/*", "credentials/*", "secrets/*"
    ],
    "require_confirmation": [
        "rm -rf", "git push --force", "docker rm",
        "DROP TABLE", "format", "shutdown"
    ]
}
```

## Layer 2: Role Verification

Before any action, verify:

```python
class RoleVerifier:
    """Verify agent role before taking action."""
    
    def __init__(self, agent_role, allowed_actions):
        self.role = agent_role
        self.allowed = allowed_actions
        
    def can_perform(self, action, target):
        """Check if agent can perform this action."""
        
        # Check role permissions
        if action not in self.allowed:
            return False, f"Role {self.role} cannot {action}"
            
        # Check target restrictions
        if self._is_no_go_zone(target):
            return False, f"Target {target} is in no-go zone"
            
        # Check if action matches role
        if not self._action_matches_role(action):
            return False, f"Action {action} doesn't match role {self.role}"
            
        return True, "Allowed"
        
    def _is_no_go_zone(self, target):
        """Check if target is protected."""
        for zone in NO_GO_ZONES["never_delete"]:
            if zone in target:
                return True
        return False
        
    def _action_matches_role(self, action):
        """Check if action matches agent role."""
        role_actions = {
            "planner": ["read", "analyze", "plan"],
            "executor": ["write", "edit", "create", "delete"],
            "reviewer": ["read", "analyze", "comment"],
            "tester": ["read", "run", "test"],
            "monitor": ["read", "check", "alert"],
        }
        return action in role_actions.get(self.role, [])
```

## Layer 3: Confirmation Prompts

For dangerous actions, ALWAYS ask:

```python
class ConfirmationPrompt:
    """Ask for confirmation before dangerous actions."""
    
    DANGEROUS_ACTIONS = [
        "delete", "overwrite", "deploy", "push",
        "restart", "format", "drop", "remove"
    ]
    
    def needs_confirmation(self, action, target):
        """Check if action needs confirmation."""
        
        # Always confirm these actions
        if action in self.DANGEROUS_ACTIONS:
            return True
            
        # Confirm if targeting protected files
        if self._is_protected(target):
            return True
            
        # Confirm if affecting multiple files
        if isinstance(target, list) and len(target) > 5:
            return True
            
        return False
        
    def prompt_user(self, action, target, details):
        """Show confirmation prompt to user."""
        
        message = f"""
CONFIRMATION REQUIRED
Action: {action}
Target: {target}
Details: {details}

Do you want to proceed?
[Y] Yes, do it
[N] No, skip this
[V] View details first
"""
        return self._get_user_input(message)
```

## Layer 4: Hallucination Prevention

Before any action, VERIFY:

```python
class HallucinationChecker:
    """Prevent LLM hallucinations from causing damage."""
    
    def verify_before_act(self, action, target, code):
        """Verify action is valid before executing."""
        
        checks = [
            self._file_exists(target),
            self._path_is_valid(target),
            self._code_is_valid(code),
            self._action_is_safe(action),
            self._no_syntax_errors(code),
            self._no_import_errors(code),
        ]
        
        failed = [c for c in checks if not c[0]]
        
        if failed:
            return False, f"Hallucination detected: {failed}"
            
        return True, "Verified"
        
    def _file_exists(self, path):
        """Check if file exists."""
        return Path(path).exists(), f"File {path} exists"
        
    def _path_is_valid(self, path):
        """Check if path is valid."""
        try:
            Path(path).resolve()
            return True, f"Path {path} is valid"
        except:
            return False, f"Path {path} is invalid"
            
    def _code_is_valid(self, code):
        """Check if code has syntax errors."""
        try:
            compile(code, '<string>', 'exec')
            return True, "Code syntax is valid"
        except SyntaxError as e:
            return False, f"Syntax error: {e}"
            
    def _action_is_safe(self, action):
        """Check if action is safe."""
        safe_actions = ["read", "analyze", "plan", "comment"]
        if action in safe_actions:
            return True, f"Action {action} is safe"
        return False, f"Action {action} needs verification"
```

## Layer 5: Audit Log

Track EVERYTHING:

```python
class AuditLog:
    """Log all agent actions for review."""
    
    def __init__(self, log_path=".sisyphus/audit.log"):
        self.log_path = Path(log_path)
        
    def log_action(self, agent, action, target, result, details=""):
        """Log an action."""
        
        entry = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "agent": agent,
            "action": action,
            "target": target,
            "result": result,
            "details": details,
            "verified": self._verify_result(result),
        }
        
        with open(self.log_path, "a") as f:
            f.write(json.dumps(entry) + "\n")
            
    def _verify_result(self, result):
        """Verify action result."""
        # Check if action succeeded
        # Check if file still exists
        # Check if no errors
        return True
        
    def get_recent_actions(self, count=50):
        """Get recent actions for review."""
        with open(self.log_path, "r") as f:
            lines = f.readlines()
            return [json.loads(line) for line in lines[-count:]]
```

## Implementation: The Safety Guard

```python
class SafetyGuard:
    """5-layer safety system for all automations."""
    
    def __init__(self, agent_role):
        self.role_verifier = RoleVerifier(agent_role, ALLOWED_ACTIONS)
        self.confirmation = ConfirmationPrompt()
        self.hallucination = HallucinationChecker()
        self.audit = AuditLog()
        
    def safe_execute(self, action, target, code=None):
        """Execute action with full safety checks."""
        
        # Layer 1: No-go zones
        if self._is_no_go_zone(target):
            self.audit.log_action(self.role, action, target, "BLOCKED", "No-go zone")
            return False, "Blocked: no-go zone"
            
        # Layer 2: Role verification
        can_do, reason = self.role_verifier.can_perform(action, target)
        if not can_do:
            self.audit.log_action(self.role, action, target, "DENIED", reason)
            return False, f"Denied: {reason}"
            
        # Layer 3: Confirmation (if dangerous)
        if self.confirmation.needs_confirmation(action, target):
            confirmed = self.confirmation.prompt_user(action, target, code)
            if not confirmed:
                self.audit.log_action(self.role, action, target, "CANCELLED", "User declined")
                return False, "Cancelled by user"
                
        # Layer 4: Hallucination check
        if code:
            verified, reason = self.hallucination.verify_before_act(action, target, code)
            if not verified:
                self.audit.log_action(self.role, action, target, "FAILED", reason)
                return False, f"Verification failed: {reason}"
                
        # Layer 5: Execute and log
        result = self._execute(action, target, code)
        self.audit.log_action(self.role, action, target, "SUCCESS" if result else "FAILED")
        
        return result, "Executed"
```

## The Rule

> **5-layer safety system: (1) No-go zones prevent absolute disasters. (2) Role verification ensures right agent does right job. (3) Confirmation prompts for dangerous actions. (4) Hallucination prevention checks file existence and code validity. (5) Audit log tracks everything for review and rollback.**
