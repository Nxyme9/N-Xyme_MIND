#!/usr/bin/env python3
"""
Security Agent Test Script
Tests the security-agent service endpoints
"""

import requests
import json

SECURITY_AGENT_URL = "http://localhost:5004"


def test_health():
    """Test health endpoint"""
    response = requests.get(f"{SECURITY_AGENT_URL}/health")
    print(f"Health check: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    return response.status_code == 200


def test_analyze_safe():
    """Test analysis of safe command"""
    payload = {"command": "ls -la", "context": {"cwd": "/home/user"}}
    response = requests.post(f"{SECURITY_AGENT_URL}/analyze", json=payload)
    print(f"\nSafe command analysis: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    return response.json()["decision"] == "allow"


def test_analyze_dangerous():
    """Test analysis of dangerous command"""
    payload = {
        "command": "rm -rf /",
        "context": {"cwd": "/home/user"},
        "skip_cache": True,
    }
    response = requests.post(f"{SECURITY_AGENT_URL}/analyze", json=payload)
    print(f"\nDangerous command analysis: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    return response.json()["decision"] == "deny"


def test_analyze_sensitive():
    """Test analysis of command with sensitive patterns"""
    payload = {
        "command": "export API_KEY=secret123",
        "context": {"cwd": "/home/user"},
        "skip_cache": True,
    }
    response = requests.post(f"{SECURITY_AGENT_URL}/analyze", json=payload)
    print(f"\nSensitive command analysis: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    return response.json()["decision"] == "prompt"


if __name__ == "__main__":
    print("=== Security Agent Tests ===")
    print(f"Testing {SECURITY_AGENT_URL}")

    tests = [
        ("Health", test_health),
        ("Safe Command", test_analyze_safe),
        ("Dangerous Command", test_analyze_dangerous),
        ("Sensitive Command", test_analyze_sensitive),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\nERROR in {name}: {e}")
            results.append((name, False))

    print("\n=== Results ===")
    for name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status} - {name}")

    all_passed = all(passed for _, passed in results)
    print(f"\nOverall: {'ALL TESTS PASSED' if all_passed else 'SOME TESTS FAILED'}")
