"""Request Validator — Validates and sanitizes incoming requests."""

import re
from typing import Optional, Tuple


class RequestValidator:
    def __init__(self, max_prompt_length: int = 100000, max_system_prompt_length: int = 10000):
        self.max_prompt_length = max_prompt_length
        self.max_system_prompt_length = max_system_prompt_length
        # Pattern to detect potential injection attempts
        self._injection_patterns = [
            r'<script[^>]*>', r'javascript:', r'on\w+\s*=',
            r'union\s+select', r'drop\s+table', r';\s*rm\s+-rf',
        ]
        self._injection_re = re.compile('|'.join(self._injection_patterns), re.IGNORECASE)

    def validate(self, prompt: str, system_prompt: str = "") -> Tuple[bool, Optional[str]]:
        """Validate request. Returns (is_valid, error_message)."""
        if not prompt or not prompt.strip():
            return False, "Prompt cannot be empty"
        if len(prompt) > self.max_prompt_length:
            return False, f"Prompt too long: {len(prompt)} > {self.max_prompt_length}"
        if system_prompt and len(system_prompt) > self.max_system_prompt_length:
            return False, f"System prompt too long: {len(system_prompt)} > {self.max_system_prompt_length}"
        # Check for injection attempts
        if self._injection_re.search(prompt):
            return False, "Potential injection attempt detected"
        if system_prompt and self._injection_re.search(system_prompt):
            return False, "Potential injection attempt detected in system prompt"
        return True, None

    def sanitize(self, text: str) -> str:
        """Sanitize text by removing potentially dangerous content."""
        # Remove script tags and event handlers
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'on\w+\s*=\s*["\'][^"\']*["\']', '', text, flags=re.IGNORECASE)
        return text.strip()


# Global instance
request_validator = RequestValidator()
