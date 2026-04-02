#!/usr/bin/env python3
"""
N-Xyme MIND Migration Verification Script
Verifies that migration completed successfully.
"""

import os
import sys
import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Tuple


# ANSI colors
class Colors:
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    CYAN = "\033[96m"
    RESET = "\033[0m"


def print_success(msg: str):
    print(f"{Colors.GREEN}✓ {msg}{Colors.RESET}")


def print_warning(msg: str):
    print(f"{Colors.YELLOW}⚠ {msg}{Colors.RESET}")


def print_error(msg: str):
    print(f"{Colors.RED}✗ {msg}{Colors.RESET}")


def print_info(msg: str):
    print(f"{Colors.CYAN}{msg}{Colors.RESET}")


class MigrationVerifier:
    def __init__(self, target_root: Path):
        self.target_root = target_root
        self.results: Dict[str, List[Tuple[str, bool, str]]] = {
            "structure": [],
            "files": [],
            "databases": [],
            "configs": [],
            "python": [],
        }

    def verify_structure(self):
        """Verify directory structure."""
        print_info("\n--- Verifying Directory Structure ---")

        required_dirs = [
            "jarvis",
            "jarvis/engine",
            "jarvis/agent",
            "jarvis/skills",
            "jarvis/adhd",
            "jarvis/ui",
            "jarvis/api",
            "configs",
            "configs/jarvis",
            "configs/opencode",
            "configs/agents",
            "scripts",
            "memory",
            ".sisyphus",
            ".sisyphus/rules",
            "data",
        ]

        for dir_path in required_dirs:
            full_path = self.target_root / dir_path
            exists = full_path.exists() and full_path.is_dir()
            status = "exists" if exists else "missing"
            if exists:
                print_success(f"  {dir_path}")
            else:
                print_error(f"  {dir_path}")
            self.results["structure"].append((dir_path, exists, status))

    def verify_files(self):
        """Verify critical files exist."""
        print_info("\n--- Verifying Critical Files ---")

        critical_files = [
            "jarvis/main.py",
            "jarvis/__init__.py",
            "memory/global_memory.py",
            "memory/session_archiver.py",
            "scripts/start-mind.py",
            "scripts/start-mind.bat",
            ".env.example",
            "docker-compose.yml",
            "package.json",
            "pyproject.toml",
            "requirements.txt",
        ]

        for file_path in critical_files:
            full_path = self.target_root / file_path
            exists = full_path.exists() and full_path.is_file()
            status = "exists" if exists else "missing"
            if exists:
                print_success(f"  {file_path}")
            else:
                print_error(f"  {file_path}")
            self.results["files"].append((file_path, exists, status))

    def verify_databases(self):
        """Verify database files."""
        print_info("\n--- Verifying Databases ---")

        db_files = [
            "data/jarvis_events.db",
            "data/jarvis_memory.db",
            "data/jarvis_scheduler.db",
            "data/nxyme.db",
        ]

        for db_path in db_files:
            full_path = self.target_root / db_path
            if full_path.exists():
                try:
                    conn = sqlite3.connect(str(full_path))
                    cursor = conn.cursor()
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                    tables = cursor.fetchall()
                    conn.close()
                    print_success(f"  {db_path} ({len(tables)} tables)")
                    self.results["databases"].append(
                        (db_path, True, f"valid ({len(tables)} tables)")
                    )
                except Exception as e:
                    print_error(f"  {db_path}: {e}")
                    self.results["databases"].append((db_path, False, f"corrupt: {e}"))
            else:
                print_warning(f"  {db_path}: not found")
                self.results["databases"].append((db_path, False, "not found"))

    def verify_configs(self):
        """Verify configuration files are valid JSON."""
        print_info("\n--- Verifying Configuration Files ---")

        config_patterns = ["configs/jarvis/*.json", "configs/opencode/*.json", ".sisyphus/*.json"]

        for pattern in config_patterns:
            for config_file in self.target_root.glob(pattern):
                try:
                    with open(config_file, "r", encoding="utf-8") as f:
                        json.load(f)
                    rel_path = config_file.relative_to(self.target_root)
                    print_success(f"  {rel_path}")
                    self.results["configs"].append((str(rel_path), True, "valid JSON"))
                except json.JSONDecodeError as e:
                    rel_path = config_file.relative_to(self.target_root)
                    print_error(f"  {rel_path}: {e}")
                    self.results["configs"].append((str(rel_path), False, f"invalid JSON: {e}"))
                except Exception as e:
                    rel_path = config_file.relative_to(self.target_root)
                    print_warning(f"  {rel_path}: {e}")
                    self.results["configs"].append((str(rel_path), False, str(e)))

    def verify_python_syntax(self):
        """Verify Python files have valid syntax."""
        print_info("\n--- Verifying Python Syntax ---")

        python_files = ["jarvis/main.py", "memory/global_memory.py", "scripts/start-mind.py"]

        for py_file in python_files:
            full_path = self.target_root / py_file
            if full_path.exists():
                try:
                    with open(full_path, "r", encoding="utf-8") as f:
                        compile(f.read(), str(full_path), "exec")
                    print_success(f"  {py_file}")
                    self.results["python"].append((py_file, True, "valid syntax"))
                except SyntaxError as e:
                    print_error(f"  {py_file}: {e}")
                    self.results["python"].append((py_file, False, f"syntax error: {e}"))
            else:
                print_warning(f"  {py_file}: not found")
                self.results["python"].append((py_file, False, "not found"))

    def check_catalyst_references(self):
        """Check for remaining CATALYST references."""
        print_info("\n--- Checking for CATALYST References ---")

        catalyst_refs = []
        for ext in ["*.py", "*.json", "*.yaml", "*.md", "*.ps1", "*.bat"]:
            for file_path in self.target_root.rglob(ext):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        if "CATALYST" in content:
                            rel_path = file_path.relative_to(self.target_root)
                            catalyst_refs.append(str(rel_path))
                except (OSError, UnicodeDecodeError) as e:
                    print(f"Warning: Could not read {file_path}: {e}")

        if catalyst_refs:
            print_warning(f"  Found {len(catalyst_refs)} files with CATALYST references:")
            for ref in catalyst_refs[:10]:  # Show first 10
                print_warning(f"    - {ref}")
            if len(catalyst_refs) > 10:
                print_warning(f"    ... and {len(catalyst_refs) - 10} more")
        else:
            print_success("  No CATALYST references found")

    def generate_report(self) -> Dict:
        """Generate verification report."""
        report = {
            "timestamp": __import__("datetime").datetime.now().isoformat(),
            "target": str(self.target_root),
            "results": self.results,
            "summary": {},
        }

        for category, items in self.results.items():
            success = sum(1 for _, passed, _ in items if passed)
            failed = sum(1 for _, passed, _ in items if not passed)
            report["summary"][category] = {
                "total": len(items),
                "success": success,
                "failed": failed,
            }

        return report

    def run(self):
        """Run all verification checks."""
        print_info("\n=== N-Xyme MIND Migration Verification ===\n")

        if not self.target_root.exists():
            print_error(f"Target directory not found: {self.target_root}")
            return False

        self.verify_structure()
        self.verify_files()
        self.verify_databases()
        self.verify_configs()
        self.verify_python_syntax()
        self.check_catalyst_references()

        # Generate report
        report = self.generate_report()

        # Summary
        print_info("\n=== Verification Summary ===")
        total_success = sum(s["success"] for s in report["summary"].values())
        total_failed = sum(s["failed"] for s in report["summary"].values())
        total_items = sum(s["total"] for s in report["summary"].values())

        print_success(f"Passed: {total_success}/{total_items}")
        if total_failed > 0:
            print_error(f"Failed: {total_failed}/{total_items}")

        # Save report
        report_path = self.target_root / "verification-report.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print_info(f"\nReport saved: {report_path}")

        print_info("\n=== Verification Complete ===\n")

        return total_failed == 0


def main():
    """Main entry point."""
    target_root = Path(r"D:\01_CODING\00_N-Xyme_MIND")

    verifier = MigrationVerifier(target_root)
    success = verifier.run()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
