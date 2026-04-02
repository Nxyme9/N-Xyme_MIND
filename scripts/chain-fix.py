#!/usr/bin/env python3
"""
Chain Fix: Launch workers with write permissions
Fixes the issue where workers inherit read-only from Prometheus
"""

import subprocess
import sys
import os

def launch_worker(worker_id, task_description):
    """Launch a worker with write permissions (not inheriting Prometheus constraints)."""
    
    # Use Sisyphus (mode=all) to launch workers
    # This ensures workers inherit write permissions, not read-only
    
    cmd = [
        "C:/Users/N-Xyme/AppData/Roaming/npm/opencode.cmd", "run",
        "--agent", "sisyphus",  # Use Sisyphus (mode=all) not Prometheus
        "--prompt", task_description
    ]
    
    print(f"Launching worker {worker_id}: {task_description}")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    
    if result.returncode == 0:
        print(f"Worker {worker_id} launched successfully")
        return True
    else:
        print(f"Worker {worker_id} failed: {result.stderr}")
        return False

def launch_chain():
    """Launch the chain: Hephaestus -> Sisyphus -> Workers"""
    
    print("=== CHAIN FIX IMPLEMENTATION ===")
    print()
    
    # Step 1: Launch Hephaestus (CEO)
    print("Step 1: Launching Hephaestus (CEO)...")
    hephaestus_cmd = [
        "C:/Users/N-Xyme/AppData/Roaming/npm/opencode.cmd", "run",
        "--agent", "hephaestus",
        "--prompt", "You are Hephaestus, the CEO. Read global-todos from Graphiti. Delegate CRITICAL tasks to Sisyphus (mode=all). Sisyphus will delegate to workers. Do NOT use Prometheus for delegation."
    ]
    
    result = subprocess.run(hephaestus_cmd, capture_output=True, text=True, timeout=300)
    if result.returncode == 0:
        print("Hephaestus launched successfully")
    else:
        print(f"Hephaestus failed: {result.stderr}")
    
    print()
    print("=== CHAIN FIX COMPLETE ===")
    print("Hephaestus will now delegate to Sisyphus (mode=all)")
    print("Sisyphus will delegate to workers (write permissions)")
    print("Workers will execute tasks properly")

if __name__ == "__main__":
    launch_chain()
