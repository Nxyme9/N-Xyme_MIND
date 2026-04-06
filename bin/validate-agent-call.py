#!/usr/bin/env python3
"""
Pre-flight validation for agent task() calls.
Validates parameters before calling task() to prevent errors.
"""

import sys
import json

VALID_SUBAGENT_TYPES = {
    "explore", "librarian", "oracle", "metis", "momus", 
    "plan", "hephaestus", "sisyphus", "prometheus", 
    "atlas", "sisyphus-junior", "multimodal-looker"
}

VALID_CATEGORIES = {
    "visual-engineering", "ultrabrain", "deep", "artistry", 
    "quick", "unspecified-low", "unspecified-high", "routing", "writing"
}

REQUIRED_PARAMS = {"load_skills", "run_in_background"}

def validate_task_call(kwargs):
    """Validate task() call parameters. Returns (is_valid, errors)"""
    errors = []
    
    # Check 1: subagent_type OR category (not both, not neither)
    has_subagent = "subagent_type" in kwargs
    has_category = "category" in kwargs
    
    if has_subagent and has_category:
        errors.append("ERROR: Cannot use both subagent_type AND category. Use ONE.")
    elif not has_subagent and not has_category:
        errors.append("ERROR: Must provide subagent_type OR category.")
    
    # Check 2: Valid subagent_type
    if has_subagent and kwargs["subagent_type"] not in VALID_SUBAGENT_TYPES:
        errors.append(f"ERROR: Invalid subagent_type '{kwargs['subagent_type']}'. Valid: {VALID_SUBAGENT_TYPES}")
    
    # Check 3: Valid category
    if has_category and kwargs["category"] not in VALID_CATEGORIES:
        errors.append(f"ERROR: Invalid category '{kwargs['category']}'. Valid: {VALID_CATEGORIES}")
    
    # Check 4: Required parameters
    for param in REQUIRED_PARAMS:
        if param not in kwargs:
            errors.append(f"ERROR: Missing required parameter '{param}'.")
    
    # Check 5: load_skills must be list
    if "load_skills" in kwargs and not isinstance(kwargs["load_skills"], list):
        errors.append("ERROR: load_skills must be a list (e.g., [] or ['skill-1']).")
    
    # Check 6: run_in_background must be bool
    if "run_in_background" in kwargs and not isinstance(kwargs["run_in_background"], bool):
        errors.append("ERROR: run_in_background must be bool (true/false).")
    
    # Check 7: prompt must be non-empty
    if "prompt" not in kwargs or not kwargs["prompt"] or len(kwargs["prompt"].strip()) < 50:
        errors.append("ERROR: prompt must be non-empty and substantive (50+ chars).")
    
    # Check 8: description must be concise
    if "description" not in kwargs or len(kwargs.get("description", "")) > 50:
        errors.append("ERROR: description must be concise (3-5 words, <50 chars).")
    
    return len(errors) == 0, errors

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 validate-agent-call.py '{\"subagent_type\": \"explore\", ...}'")
        sys.exit(1)
    
    try:
        kwargs = json.loads(sys.argv[1])
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON: {e}")
        sys.exit(1)
    
    is_valid, errors = validate_task_call(kwargs)
    
    if is_valid:
        print("✅ VALID — All 8 checks passed. Safe to call task().")
        sys.exit(0)
    else:
        print("❌ INVALID — Fix these errors before calling task():")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)
