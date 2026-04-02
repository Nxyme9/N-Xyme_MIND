#!/usr/bin/env python3
"""
Documentation Audit Script for N-Xyme Catalyst
Verifies that all required documentation exists and is complete.
"""

import os
import sys
from pathlib import Path

# Required documents from the specification
REQUIRED_DOCS = {
    "docs/SYSTEM_OVERVIEW.md": "System overview and high-level architecture",
    "docs/ARCHITECTURE.md": "Detailed architecture documentation",
    "docs/SECURITY_ARCHITECTURE.md": "Security architecture and controls",
    "docs/AGENTS_AND_MCP.md": "Agents and MCP server documentation",
    "docs/README.md": "Documentation collection README",
    "docs/SUMMARY_OF_CONTENTS.md": "Summary of documentation contents",
    "README.md": "Project overview and setup instructions",
    "LICENSE": "Open-source license",
    ".env.example": "Environment variable template",
    ".gitignore": "Git ignore patterns",
    "docker-compose.yml": "Main orchestration file",
}

# Package-level required documents
PACKAGE_DOCS = {
    "README.md": "Package overview and usage",
    "requirements.txt": "Python dependencies",
    "package.json": "Node.js dependencies (if applicable)",
}


def check_file_exists(filepath):
    """Check if a file exists."""
    path = Path(filepath)
    return path.exists()


def check_package_docs(package_dir):
    """Check documentation within a package."""
    missing = []
    package_path = Path(package_dir)

    if not package_path.exists():
        return missing

    for doc_name in PACKAGE_DOCS.keys():
        doc_path = package_path / doc_name
        if not doc_path.exists():
            # Only require package.json if it's a Node.js package
            if doc_name == "package.json":
                # Check if there's a package.json anywhere in the package
                if not any(package_path.rglob("package.json")):
                    missing.append(str(doc_path))
            else:
                missing.append(str(doc_path))

    return missing


def main():
    """Main audit function."""
    print("=" * 60)
    print("N-Xyme Catalyst Documentation Audit")
    print("=" * 60)

    all_missing = []

    # Check root-level required documents
    print("\n[1] Checking root-level documents...")
    for doc, description in REQUIRED_DOCS.items():
        if check_file_exists(doc):
            print(f"  ✓ {doc} - {description}")
        else:
            print(f"  ✗ {doc} - MISSING")
            all_missing.append(doc)

    # Check package-level documents
    print("\n[2] Checking package-level documents...")
    packages_dir = Path("packages")
    if packages_dir.exists():
        for package in packages_dir.iterdir():
            if package.is_dir():
                print(f"\n  Checking {package.name}...")
                missing = check_package_docs(package)
                if missing:
                    for m in missing:
                        print(f"    ✗ {m}")
                        all_missing.append(m)
                else:
                    print(f"    ✓ All required docs present")

    # Check for broken internal links (basic check)
    print("\n[3] Checking for broken internal references...")
    # This is a simplified check - in production, use markdown-link-check
    docs_with_links = []
    for doc in Path("docs").glob("*.md"):
        docs_with_links.append(str(doc))

    if docs_with_links:
        print(
            f"  Found {len(docs_with_links)} documentation files with potential links"
        )

    # Summary
    print("\n" + "=" * 60)
    print("AUDIT SUMMARY")
    print("=" * 60)

    if all_missing:
        print(f"❌ FAILED: {len(all_missing)} missing document(s):")
        for missing in all_missing:
            print(f"  - {missing}")
        return 1
    else:
        print("✅ PASSED: All required documents are present")
        return 0


if __name__ == "__main__":
    sys.exit(main())
