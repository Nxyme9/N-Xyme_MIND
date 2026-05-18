#!/usr/bin/env python3
"""
Native Replacement Audit Script

This script identifies Python-dependent components that have been replaced
by native Rust implementations and reports on Python dependencies that
can potentially be removed.

This is an AUDIT ONLY - nothing is deleted.
"""

import os
import sys
from pathlib import Path

# Base directory
BASE_DIR = Path("/home/nxyme/N-Xyme_CODE/N-Xyme_MIND")


def check_file_exists(path: Path) -> bool:
    """Check if a file exists."""
    return path.exists()


def check_rust_source(source_name: str) -> tuple[bool, str]:
    """Check if Rust source exists and is built."""
    # Check for .rs file in scripts
    rs_path = BASE_DIR / "scripts" / f"{source_name}.rs"
    if not rs_path.exists():
        return False, f"scripts/{source_name}.rs not found"

    # Check for compiled binary in target/release
    binary_path = BASE_DIR / "target" / "release" / source_name
    if not binary_path.exists():
        # Also check without extension
        binary_path = BASE_DIR / "target" / "release" / f"{source_name}"
        if not binary_path.exists():
            return False, f"Compiled binary not found at target/release/{source_name}"

    return True, f"Found Rust source at {rs_path} and compiled binary"


def check_service_rust(service_name: str) -> tuple[bool, str]:
    """Check if a service has Rust source and is built."""
    service_path = BASE_DIR / "services" / service_name

    if not service_path.exists():
        return False, f"Service directory services/{service_name} not found"

    # Check for Cargo.toml
    cargo_toml = service_path / "Cargo.toml"
    if not cargo_toml.exists():
        return False, f"Cargo.toml not found in services/{service_name}"

    # Check if src has files
    src_path = service_path / "src"
    if not src_path.exists():
        return False, f"src/ directory not found in services/{service_name}"

    # Check for any .rs files
    rs_files = list(src_path.glob("*.rs"))
    if not rs_files:
        return False, f"No .rs source files in services/{service_name}/src (src/ directory is empty)"

    # Check for compiled binary (common patterns)
    binary_names = [
        f"lib{service_name}.so",
        f"lib{service_name}.a",
        service_name,
        f"{service_name}-cli",
    ]

    for binary_name in binary_names:
        for release_dir in ["target/release", "target/debug"]:
            binary_path = BASE_DIR / release_dir / "deps" / binary_name
            if binary_path.exists():
                return True, f"Found compiled library: {binary_path}"

            binary_path = BASE_DIR / release_dir / binary_name
            if binary_path.exists():
                return True, f"Found compiled binary: {binary_path}"

    return False, "No compiled binary found (project not built)"


def check_tool_in_rust(file_path: Path, tool_name: str) -> tuple[bool, str]:
    """Check if a tool exists in a Rust source file."""
    if not file_path.exists():
        return False, f"Source file {file_path} not found"

    try:
        content = file_path.read_text()
        if tool_name in content:
            return True, f"Found '{tool_name}' in {file_path}"
        else:
            return False, f"'{tool_name}' not found in {file_path}"
    except Exception as e:
        return False, f"Error reading {file_path}: {e}"


def main():
    print("=" * 70)
    print("NATIVE REPLACEMENT AUDIT REPORT")
    print("=" * 70)
    print()

    # Track replacements
    replaced = []
    pending = []

    # =========================================================================
    # 1. sync-agents.js -> scripts/sync-agents.rs + compiled binary
    # =========================================================================
    print("[1] Checking sync-agents replacement...")
    print("-" * 50)

    js_path = BASE_DIR / "scripts" / "sync-agents.js"
    if js_path.exists():
        print(f"  Original Python: scripts/sync-agents.js EXISTS")

        rs_exists, rs_msg = check_rust_source("sync-agents")
        if rs_exists:
            print(f"  Rust replacement: YES - {rs_msg}")
            print(f"  Python deps removable: none (JS-only script)")
            replaced.append({
                "component": "sync-agents.js",
                "new_version": "scripts/sync-agents.rs (Rust binary)",
                "python_deps": "none (pure JS script)"
            })
        else:
            print(f"  Rust replacement: NO - {rs_msg}")
            print(f"  Status: PENDING - Rust version not yet implemented")
            pending.append({
                "component": "sync-agents.js",
                "native_version": "scripts/sync-agents.rs (Rust)",
                "python_deps": "none (pure JS script)",
                "status": "Rust source and binary not found"
            })
    else:
        print(f"  Original: NOT FOUND (may already be removed)")

    print()

    # =========================================================================
    # 2. Embedding server -> services/minilm/
    # =========================================================================
    print("[2] Checking embedding server (minilm) replacement...")
    print("-" * 50)

    # Check for Python embedding server
    embedding_server_paths = [
        BASE_DIR / "services" / "embedding-server",
        BASE_DIR / "services" / "embed-server",
    ]

    embedding_server_found = False
    for path in embedding_server_paths:
        if path.exists():
            print(f"  Original Python: services/{path.name} EXISTS")
            embedding_server_found = True
            break

    if not embedding_server_found:
        print("  Original Python: No embedding-server found")

    # Check for Rust minilm
    minilm_exists, minilm_msg = check_service_rust("minilm")
    if minilm_exists:
        print(f"  Rust replacement: YES - {minilm_msg}")
        print(f"  Python deps removable: sentence-transformers, torch, numpy (embedding inference)")
        replaced.append({
            "component": "embedding-server (Python)",
            "new_version": "services/minilm/ (Rust native)",
            "python_deps": "sentence-transformers, torch, numpy"
        })
    else:
        print(f"  Rust replacement: NO - {minilm_msg}")
        print(f"  Status: PENDING - Rust minilm not built or source empty")
        pending.append({
            "component": "embedding-server (Python)",
            "native_version": "services/minilm/ (Rust)",
            "python_deps": "sentence-transformers, torch, numpy",
            "status": minilm_msg
        })

    print()

    # =========================================================================
    # 3. Session digest -> grep session_digest in nx-agents-mcp
    # =========================================================================
    print("[3] Checking session_digest tool replacement...")
    print("-" * 50)

    main_rs = BASE_DIR / "services" / "nx-agents-mcp" / "src" / "main.rs"

    # Check for Python session digest (look for related Python files)
    python_session_digest_paths = [
        BASE_DIR / "services" / "nx-agents-mcp" / "session_digest.py",
    ]

    python_sd_found = False
    for path in python_session_digest_paths:
        if path.exists():
            print(f"  Original Python: {path} EXISTS")
            python_sd_found = True

    if not python_sd_found:
        print("  Original Python: session_digest.py not found")

    # Check for Rust implementation
    rust_sd_exists, rust_sd_msg = check_tool_in_rust(main_rs, "session_digest")
    if rust_sd_exists:
        print(f"  Rust replacement: YES - {rust_sd_msg}")
        print(f"  Python deps removable: (if session_digest was Python module)")
        replaced.append({
            "component": "session_digest tool",
            "new_version": "services/nx-agents-mcp/src/main.rs (Rust)",
            "python_deps": "N/A - tool was likely embedded"
        })
    else:
        print(f"  Rust replacement: NO - {rust_sd_msg}")
        print(f"  Status: PENDING - session_digest tool not implemented in Rust")
        pending.append({
            "component": "session_digest tool",
            "native_version": "services/nx-agents-mcp/src/main.rs (Rust)",
            "python_deps": "N/A",
            "status": rust_sd_msg
        })

    print()

    # =========================================================================
    # 4. whisper.cpp -> services/llamabridge/libwhisper.so
    # =========================================================================
    print("[4] Checking whisper.cpp (speech-to-text) replacement...")
    print("-" * 50)

    # Check for Python whisper (likely was openai-whisper package)
    print("  Original Python: openai (whisper) - check requirements.txt")

    # Check for Rust whisper library
    libwhisper_paths = [
        BASE_DIR / "services" / "llamabridge" / "libwhisper.so",
        BASE_DIR / "target" / "release" / "libwhisper.so",
        BASE_DIR / "target" / "debug" / "libwhisper.so",
    ]

    libwhisper_found = False
    for path in libwhisper_paths:
        if path.exists():
            print(f"  Rust replacement: YES - Found at {path}")
            libwhisper_found = True
            break

    if not libwhisper_found:
        print("  Rust replacement: NO - libwhisper.so not found")
        print("  Status: PENDING - Native whisper library not compiled")
        pending.append({
            "component": "whisper.cpp (speech-to-text)",
            "native_version": "services/llamabridge/libwhisper.so",
            "python_deps": "openai (for whisper), faster-whisper, or whisper",
            "status": "Native library not built"
        })

    print()

    # =========================================================================
    # Summary
    # =========================================================================
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print()

    print("REPLACED COMPONENTS (Native implementations found):")
    print("-" * 50)
    if replaced:
        for i, item in enumerate(replaced, 1):
            print(f"  {i}. {item['component']}")
            print(f"     New version: {item['new_version']}")
            print(f"     Python deps no longer needed: {item['python_deps']}")
            print()
    else:
        print("  None - no components have been fully replaced yet.")
        print()

    print("PENDING REPLACEMENTS:")
    print("-" * 50)
    if pending:
        for i, item in enumerate(pending, 1):
            print(f"  {i}. {item['component']}")
            print(f"     Target native: {item['native_version']}")
            print(f"     Status: {item['status']}")
            print(f"     Python deps still needed: {item['python_deps']}")
            print()
    else:
        print("  All components replaced!")
        print()

    print("=" * 70)
    print("PYTHON DEPENDENCIES AUDIT")
    print("=" * 70)
    print()
    print("Based on the above analysis, these Python packages may no longer")
    print("be needed if the corresponding native implementations are used:")
    print()
    print("  - sentence-transformers (if minilm Rust is used)")
    print("  - torch (if minilm Rust is used)")
    print("  - numpy (if minilm Rust is used)")
    print("  - openai (whisper component, if native libwhisper.so is used)")
    print("  - faster-whisper (if native libwhisper.so is used)")
    print("  - whisper (if native libwhisper.so is used)")
    print()
    print("NOTE: This is an AUDIT only. No files have been deleted.")
    print("      Manual review of requirements.txt files is recommended.")
    print()


if __name__ == "__main__":
    main()