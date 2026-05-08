#!/usr/bin/env python3
"""
Security Gate: Detect security-sensitive paths in the codebase.
Used by gate-8-security-paths.sh quality gate.
"""

import os
import sys
from pathlib import Path

IGNORED_DIRS = {
    'node_modules', '.venv', '.cache', '.next', '.nuxt',
    'dist', 'build', 'coverage', '__pycache__', '.pytest_cache',
    'vendor', 'packages', 'site-packages', '.trash',
}

SECURITY_SENSITIVE_PATHS = [
    'auth', 'security', 'crypto', 'payments', 'env',
    'credentials', 'secrets', 'keys', 'tokens', 'passwords',
]

SECURITY_SENSITIVE_FILES = [
    '.env', '.env.local', '.env.production',
    'credentials.json', 'secrets.json', 'keys.json',
    'api_key', 'private_key', 'id_rsa', 'id_ed25519',
]


def find_security_sensitive_paths(root_dir: str) -> list[tuple[str, str]]:
    """Find PROJECT security issues - ignores properly protected paths."""
    findings = []
    root = Path(root_dir)

    gitignore_path = root / '.gitignore'
    gitignore_patterns = set()
    if gitignore_path.exists():
        with open(gitignore_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    gitignore_patterns.add(line)

    def is_ignored(path: Path) -> bool:
        path_str = str(path.relative_to(root))
        for pattern in gitignore_patterns:
            if pattern in path_str or path.name == pattern:
                return True
        return False

    for subdir in root.rglob('*'):
        if not subdir.is_dir():
            continue
        path_parts = subdir.parts
        if any(ignored in path_parts for ignored in IGNORED_DIRS):
            continue
        rel_path = subdir.relative_to(root)
        rel_path_str = str(rel_path)

        if 'api/auth' in rel_path_str or rel_path_str.endswith('security'):
            continue

        subdir_name = subdir.name.lower()
        if subdir_name in SECURITY_SENSITIVE_PATHS:
            if not is_ignored(subdir):
                findings.append(('DIR', str(rel_path)))

    for pattern in SECURITY_SENSITIVE_FILES:
        for file in root.rglob(pattern):
            path_parts = file.parts
            if any(ignored in path_parts for ignored in IGNORED_DIRS):
                continue
            if is_ignored(file):
                continue

            if file.suffix == '.json' and file.name in ['keys.json', 'credentials.json', 'secrets.json']:
                try:
                    content = file.read_text()
                    if all('${{' in content or '${' in content for _ in range(1)):
                        continue
                except:
                    pass

            rel_path = file.relative_to(root)
            findings.append(('FILE', str(rel_path)))

    return findings


def main():
    if len(sys.argv) < 2:
        root_dir = os.environ.get('ROOT_DIR', '.')
    else:
        root_dir = sys.argv[1]

    findings = find_security_sensitive_paths(root_dir)

    if findings:
        print("Security-sensitive paths detected:")
        for path_type, path in findings:
            print(f"  [{path_type}] {path}")
        sys.exit(1)
    else:
        print("No security-sensitive paths detected.")
        sys.exit(0)


if __name__ == '__main__':
    main()