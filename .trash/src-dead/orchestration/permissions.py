"""Permission System — Wildcard pattern matching for tool permissions.

Ported from Claude Code's permission system.
Supports patterns like: *.env, src/**/*.ts, Bash(git *)
"""

import fnmatch
import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


class PermissionBehavior(Enum):
    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"


@dataclass
class PermissionRule:
    """A single permission rule."""
    pattern: str
    behavior: PermissionBehavior
    message: str = ""
    source: str = "default"


class PermissionChecker:
    """Checks paths against a set of permission rules."""
    
    def __init__(self):
        self._rules: List[PermissionRule] = []
    
    def add_rule(self, pattern: str, behavior: PermissionBehavior, message: str = "", source: str = "default") -> None:
        """Add a permission rule."""
        self._rules.append(PermissionRule(
            pattern=pattern,
            behavior=behavior,
            message=message,
            source=source
        ))
    
    def check(self, path: str) -> Dict[str, Any]:
        """Check if a path matches any rule. Returns first matching rule."""
        for rule in self._rules:
            if self._match(rule.pattern, path):
                return {
                    'behavior': rule.behavior.value,
                    'message': rule.message,
                    'rule': rule.pattern,
                    'source': rule.source
                }
        return {'behavior': 'allow', 'message': '', 'rule': None, 'source': 'default'}
    
    def get_matching_rules(self, path: str) -> List[PermissionRule]:
        """Get all rules that match a path."""
        return [rule for rule in self._rules if self._match(rule.pattern, path)]
    
    def clear(self) -> None:
        """Clear all rules."""
        self._rules.clear()
    
    @staticmethod
    def _match(pattern: str, text: str) -> bool:
        """Match a pattern against text with wildcard support.
        
        Supports:
        - * — matches any characters except /
        - ** — matches any characters including /
        - ? — matches single character
        - [seq] — matches characters in seq
        - [!seq] — matches characters not in seq
        """
        if '**' in pattern:
            regex = pattern.replace('**', '__DOUBLESTAR__')
            regex = fnmatch.translate(regex)
            regex = regex.replace('__DOUBLESTAR__', '.*')
            return bool(re.match(regex, text, re.IGNORECASE))
        
        return fnmatch.fnmatch(text, pattern)


def create_default_deny_rules() -> PermissionChecker:
    """Create a permission checker with default deny rules."""
    checker = PermissionChecker()
    
    checker.add_rule('rm -rf *', PermissionBehavior.DENY, 'Recursive force delete is not allowed')
    checker.add_rule('rm -rf /*', PermissionBehavior.DENY, 'Root delete is not allowed')
    checker.add_rule('sudo *', PermissionBehavior.DENY, 'Sudo is not allowed')
    checker.add_rule('mkfs *', PermissionBehavior.DENY, 'Filesystem creation is not allowed')
    checker.add_rule('dd *', PermissionBehavior.DENY, 'Disk dump is not allowed')
    checker.add_rule('chmod 777 *', PermissionBehavior.DENY, 'World-writable permissions not allowed')
    checker.add_rule('curl * | *sh', PermissionBehavior.DENY, 'Remote code execution not allowed')
    checker.add_rule('wget * | *sh', PermissionBehavior.DENY, 'Remote code execution not allowed')
    
    checker.add_rule('*.env', PermissionBehavior.DENY, 'Environment files are read-only')
    checker.add_rule('*.key', PermissionBehavior.DENY, 'Key files are read-only')
    checker.add_rule('*.pem', PermissionBehavior.DENY, 'PEM files are read-only')
    
    return checker


def create_tool_permission_rules(tool_name: str, file_path: Optional[str] = None) -> PermissionChecker:
    """Create permission rules for a specific tool."""
    checker = create_default_deny_rules()
    
    if tool_name in ('file_read', 'Read', 'grep', 'glob'):
        checker.add_rule('*', PermissionBehavior.ALLOW, 'Read operations allowed')
    
    elif tool_name in ('file_edit', 'file_write', 'Edit', 'Write'):
        if file_path:
            checker.add_rule(file_path, PermissionBehavior.ALLOW, f'Write allowed for {file_path}')
        else:
            checker.add_rule('*', PermissionBehavior.ASK, 'Write requires permission')
    
    elif tool_name in ('Bash', 'bash'):
        checker.add_rule('git *', PermissionBehavior.ALLOW, 'Git operations allowed')
        checker.add_rule('ls *', PermissionBehavior.ALLOW, 'List operations allowed')
        checker.add_rule('cat *', PermissionBehavior.ALLOW, 'Cat operations allowed')
        checker.add_rule('*', PermissionBehavior.ASK, 'Other commands require permission')
    
    return checker
