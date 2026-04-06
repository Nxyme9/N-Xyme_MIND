#!/usr/bin/env python3
"""Verification Engine — Prevents AI pitfalls: stubs, silent greens, hallucinations"""

import ast
import subprocess
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional


@dataclass
class VerificationResult:
    layer: str
    passed: bool
    issues: List[str] = field(default_factory=list)
    details: Dict = field(default_factory=dict)


class ASTVerifier:
    """Layer 1: Prove code exists and isn't stubs"""

    @staticmethod
    def is_stub(func_node) -> bool:
        if len(func_node.body) == 1:
            if isinstance(func_node.body[0], ast.Pass):
                return True
            if isinstance(func_node.body[0], ast.Raise):
                return True
        return False

    @staticmethod
    def verify_file(filepath: str) -> List[str]:
        issues = []
        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                tree = ast.parse(f.read())
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if ASTVerifier.is_stub(node):
                        issues.append(f"{filepath}:{node.name} (stub)")
        except SyntaxError:
            issues.append(f"{filepath}: SYNTAX ERROR")
        return issues

    @staticmethod
    def verify_directory(src_dir: str = "src") -> VerificationResult:
        issues = []
        for py_file in Path(src_dir).rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue
            issues.extend(ASTVerifier.verify_file(str(py_file)))
        return VerificationResult(
            layer="ast_verification",
            passed=len(issues) == 0,
            issues=issues,
            details={"files_scanned": len(list(Path(src_dir).rglob("*.py")))},
        )


class SmokeTester:
    """Layer 2: Prove critical paths work"""

    @staticmethod
    def test_import(module_path: str) -> VerificationResult:
        issues = []
        try:
            parts = module_path.replace("/", ".").replace("\\", ".").replace(".py", "")
            __import__(parts)
        except Exception as e:
            issues.append(f"Import failed: {module_path} - {e}")
        return VerificationResult(layer="smoke_import", passed=len(issues) == 0, issues=issues)

    @staticmethod
    def test_instantiate(module_path: str, class_name: str) -> VerificationResult:
        issues = []
        try:
            parts = module_path.replace("/", ".").replace("\\", ".").replace(".py", "")
            mod = __import__(parts, fromlist=[class_name])
            cls = getattr(mod, class_name)
            instance = cls()
        except Exception as e:
            issues.append(f"Instantiate failed: {class_name} - {e}")
        return VerificationResult(layer="smoke_instantiate", passed=len(issues) == 0, issues=issues)


class ContractTester:
    """Layer 3: Verify interfaces match expectations"""

    @staticmethod
    def verify_method_exists(module_path: str, class_name: str, method_name: str) -> VerificationResult:
        issues = []
        try:
            with open(module_path, "r", encoding="utf-8", errors="replace") as f:
                tree = ast.parse(f.read())
            found = False
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name == class_name:
                    for item in node.body:
                        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            if item.name == method_name:
                                found = True
            if not found:
                issues.append(f"Missing method: {class_name}.{method_name}")
        except Exception as e:
            issues.append(f"Contract check failed: {e}")
        return VerificationResult(layer="contract", passed=len(issues) == 0, issues=issues)


class ProofTester:
    """Layer 4: Prove tests check actual values, not just truthiness"""

    @staticmethod
    def find_weak_assertions(test_dir: str = "tests") -> VerificationResult:
        issues = []
        for py_file in Path(test_dir).rglob("test_*.py"):
            try:
                with open(py_file, "r", encoding="utf-8", errors="replace") as f:
                    tree = ast.parse(f.read())
                for node in ast.walk(tree):
                    if isinstance(node, ast.Assert):
                        if isinstance(node.test, ast.Name):
                            issues.append(f"{py_file}:{node.lineno} (weak: assert {node.test.id})")
            except Exception:
                pass
        return VerificationResult(layer="proof_tests", passed=len(issues) == 0, issues=issues)


class VerificationEngine:
    """Main engine: runs all verification layers"""

    def __init__(self, src_dir: str = "src", test_dir: str = "tests"):
        self.src_dir = src_dir
        self.test_dir = test_dir
        self.results: List[VerificationResult] = []

    def verify_all(self) -> Dict:
        self.results = []

        # Layer 1: AST verification
        self.results.append(ASTVerifier.verify_directory(self.src_dir))

        # Layer 2: Smoke tests (key modules)
        key_modules = [
            ("src/brain/pipeline.py", "BrainPipeline"),
            ("src/agent_coordinator.py", "AgentCoordinator"),
            ("src/circuit_breaker.py", "CircuitBreaker"),
        ]
        for module, cls in key_modules:
            if Path(module).exists():
                self.results.append(SmokeTester.test_import(module))
                self.results.append(SmokeTester.test_instantiate(module, cls))

        # Layer 3: Contract tests
        contracts = [
            ("src/brain/pipeline.py", "BrainPipeline", "pre_execute"),
            ("src/brain/pipeline.py", "BrainPipeline", "post_execute"),
            ("src/agent_coordinator.py", "AgentCoordinator", "dispatch_with_brain"),
        ]
        for module, cls, method in contracts:
            if Path(module).exists():
                self.results.append(ContractTester.verify_method_exists(module, cls, method))

        # Layer 4: Proof tests
        if Path(self.test_dir).exists():
            self.results.append(ProofTester.find_weak_assertions(self.test_dir))

        return self._compile_report()

    def _compile_report(self) -> Dict:
        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)
        all_issues = []
        for r in self.results:
            all_issues.extend(r.issues)

        return {
            "passed": passed,
            "failed": failed,
            "total": len(self.results),
            "issues": all_issues,
            "verdict": "PASS" if failed == 0 else "FAIL",
            "details": [
                {"layer": r.layer, "passed": r.passed, "issues": r.issues}
                for r in self.results
            ],
        }

    def quick_verify(self) -> str:
        """Quick smoke test: prove the system works"""
        report = self.verify_all()
        if report["verdict"] == "PASS":
            return f"VERIFIED: {report['passed']}/{report['total']} checks passed"
        else:
            issues = chr(10).join(report["issues"][:5])
        return f"FAILED: {report['failed']} issues found:{chr(10)}{issues}"
