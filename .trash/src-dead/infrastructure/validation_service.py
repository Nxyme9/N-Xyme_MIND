"""Validation Service — Input validation"""

import logging, re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class Validator:
    def __init__(self):
        self._rules: Dict[str, List[dict]] = {}

    def add_rule(self, field: str, rule_type: str, **kwargs):
        if field not in self._rules:
            self._rules[field] = []
        self._rules[field].append({"type": rule_type, **kwargs})

    def validate(self, data: Dict) -> Dict[str, List[str]]:
        errors = {}
        for field, rules in self._rules.items():
            value = data.get(field)
            field_errors = []
            for rule in rules:
                if rule["type"] == "required" and not value:
                    field_errors.append(f"{field} is required")
                elif rule["type"] == "min_length" and value and len(str(value)) < rule["value"]:
                    field_errors.append(f"{field} must be at least {rule['value']} chars")
                elif rule["type"] == "max_length" and value and len(str(value)) > rule["value"]:
                    field_errors.append(f"{field} must be at most {rule['value']} chars")
                elif (
                    rule["type"] == "pattern" and value and not re.match(rule["value"], str(value))
                ):
                    field_errors.append(f"{field} invalid format")
                elif (
                    rule["type"] == "email"
                    and value
                    and not re.match(
                        r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", str(value)
                    )
                ):
                    field_errors.append(f"{field} invalid email")
            if field_errors:
                errors[field] = field_errors
        return errors

    def is_valid(self, data: Dict) -> bool:
        return len(self.validate(data)) == 0
