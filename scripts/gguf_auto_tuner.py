#!/usr/bin/env python3
"""
GGUF Auto-Tuner - Self-Optimizing llama.cpp Configuration
Automatically finds optimal flags for each model on your hardware.
"""

import json
import os
import subprocess
import time
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
import requests

CONFIG_DIR = Path.home() / ".config" / "nxyme-gguf"
CONFIG_FILE = CONFIG_DIR / "optimized_configs.json"
HARDWARE_PROFILE = CONFIG_DIR / "hardware_profile.json"

CPU_MODEL = "AMD Ryzen 7 7800X3D"
GPU_MODEL = "RTX 3080 Ti"

THREAD_OPTIONS = [4, 8, 12, 16, 32]
GPU_LAYER_OPTIONS = [0, 33, 66, 99]
CONTEXT_SIZES = [2048, 4096, 8192]

class GGUF AutoTuner:
    def __init__(self, model_path: str, server_bin: str = "/home/nxyme/llama.cpp/build/bin/llama-server"):
        self.model_path = model_path
        self.model_name = Path(model_path).stem
        self.server_bin = server_bin
        self.port = 8090
        self.server_pid = None
        
    def detect_hardware(self) -> Dict[str, Any]:
        """Detect and cache hardware profile"""
        result = {
            "cpu": "unknown",
            "cpu_cores": os.cpu_count(),
            "gpu": "unknown",
            "vram_mb": 0,
            "ram_gb": 0
        }
        
        try:
            cpu_info = subprocess.run(
                ["grep", "model name", "/proc/cpuinfo"],
                capture_output=True, text=True
            )
            if cpu_info.returncode == 0:
                result["cpu"] = cpu_info.stdout.split("\n")[0].split(":")[-1].strip()
        except (subprocess.SubprocessError, OSError) as e:
            print(f"Warning: Could not detect CPU: {e}")
            
        try:
            gpu_info = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
                capture_output=True, text=True
            )
            if gpu_info.returncode == 0:
                line = gpu_info.stdout.strip().split("\n")[0]
                parts = line.split(",")
                result["gpu"] = parts[0].strip()
                result["vram_mb"] = int(parts[1].strip().split()[0])
        except (subprocess.SubprocessError, OSError) as e:
            print(f"Warning: Could not detect CPU: {e}")
            
        try:
            mem_info = subprocess.run(
                ["grep", "MemTotal", "/proc/meminfo"],
                capture_output=True, text=True
            )
            if mem_info.returncode == 0:
                kb = int(mem_info.stdout.split()[1])
                result["ram_gb"] = kb // 1024 // 1024
        except (subprocess.SubprocessError, OSError) as e:
            print(f"Warning: Could not detect CPU: {e}")
            
        return result
    
    def load_saved_config(self) -> Optional[Dict]:
        """Load saved optimized config if exists"""
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE) as f:
                all_configs = json.load(f)
                return all_configs.get(self.model_name)
        return None
    
    def save_config(self, config: Dict):
        """Save optimized config"""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        
        all_configs = {}
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE) as f:
                all_configs = json.load(f)
        
        all_configs[self.model_name] = config
        
        with open(CONFIG_FILE, "w") as f:
            json.dump(all_configs, f, indent=2)
    
    def start_server(self, extra_args: str = "") -> bool:
        """Start llama-server with given args"""
        self.stop_server()
        
        cmd = f"{self.server_bin} -m {self.model_path} --port {self.port} -ngl 99 -np 1 {extra_args}"
        
        self.server_pid = subprocess.Popen(
            cmd.split(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        for _ in range(30):
            try:
                resp = requests.get(f"http://localhost:{self.port}/health", timeout=1)
                if resp.status_code == 200:
                    return True
            except (requests.RequestException, ConnectionError) as e:
                # Server not ready yet, continue waiting
            time.sleep(1)
        
        return False
    
    def stop_server(self):
        """Stop any server on our port"""
        if self.server_pid:
            try:
                self.server_pid.terminate()
                self.server_pid.wait(timeout=5)
            except (subprocess.TimeoutExpired, OSError) as e:
                print(f"Warning: Could not gracefully stop server, killing: {e}")
                self.server_pid.kill()
        
        try:
            subprocess.run(["fuser", "-k", f"{self.port}/tcp"], capture_output=True)
        except (subprocess.SubprocessError, OSError) as e:
            print(f"Warning: Could not detect CPU: {e}")
        time.sleep(1)
    
    def benchmark(self, prompt: str = "Write hello world in Python:", max_tokens: int = 100) -> float:
        """Run benchmark and return tokens/sec"""
        try:
            resp = requests.post(
                f"http://localhost:{self.port}/completions",
                json={"prompt": prompt, "max_tokens": max_tokens},
                timeout=60
            )
            if resp.status_code == 200:
                data = resp.json()
                timings = data.get("timings", {})
                pred_second = timings.get("predicted_per_second", 0)
                if pred_second > 0:
                    return pred_second
                    
                tokens = data.get("tokens_predicted", 0)
                ms = timings.get("predicted_ms", 1)
                if tokens > 0:
                    return tokens / (ms / 1000)
        except Exception as e:
            print(f"  Benchmark error: {e}")
        return 0
    
    def tune(self) -> Dict[str, Any]:
        """Auto-tune parameters for this model"""
        print(f"\n{'='*60}")
        print(f"Auto-tuning for {self.model_name}")
        print(f"{'='*60}")
        
        hardware = self.detect_hardware()
        print(f"Hardware: {hardware['cpu']} ({hardware['cpu_cores']} cores)")
        print(f"GPU: {hardware['gpu']} ({hardware['vram_mb']}MB VRAM)")
        
        saved = self.load_saved_config()
        if saved:
            print(f"\nUsing saved config: {saved}")
            return saved
        
        print("\n🔍 Testing thread configurations...")
        best_threads = 16
        best_speed = 0
        
        for threads in THREAD_OPTIONS:
            if not self.start_server(f"-t {threads}"):
                print(f"  -t {threads}: FAILED TO START")
                continue
            
            speed = self.benchmark()
            print(f"  -t {threads}: {speed:.1f} tok/s")
            self.stop_server()
            
            if speed > best_speed:
                best_speed = speed
                best_threads = threads
        
        print(f"\n🏆 Best threads: {best_threads} ({best_speed:.1f} tok/s)")
        
        print("\n🔍 Testing context sizes...")
        best_context = 4096
        best_ctx_speed = 0
        
        for ctx in CONTEXT_SIZES:
            if not self.start_server(f"-t {best_threads} -c {ctx}"):
                print(f"  -c {ctx}: FAILED TO START")
                continue
            
            speed = self.benchmark()
            print(f"  -c {ctx}: {speed:.1f} tok/s")
            self.stop_server()
            
            if speed > best_ctx_speed:
                best_ctx_speed = speed
                best_context = ctx
        
        print(f"\n🏆 Best context: {best_context} ({best_ctx_speed:.1f} tok/s)")
        
        print("\n🔍 Testing additional flags...")
        flag_tests = [
            ("--flash-attn on", "flash-attn"),
            ("--no-mmap", "no-mmap"),
            ("-ctk q4_0 -ctv q4_0", "kv-quant"),
        ]
        
        best_flags = ""
        best_flag_speed = 0
        
        for flag, name in flag_tests:
            full_flags = f"-t {best_threads} -c {best_context} {flag}"
            if not self.start_server(full_flags):
                print(f"  {name}: FAILED TO START")
                continue
            
            speed = self.benchmark()
            print(f"  {name}: {speed:.1f} tok/s")
            self.stop_server()
            
            if speed > best_flag_speed:
                best_flag_speed = speed
                best_flags = flag
        
        optimal_config = {
            "threads": best_threads,
            "context_size": best_context,
            "extra_flags": best_flags,
            "hardware": hardware,
            "speed": best_flag_speed if best_flag_speed > 0 else best_speed,
            "timestamp": time.time()
        }
        
        self.save_config(optimal_config)
        
        print(f"\n{'='*60}")
        print(f"✅ OPTIMAL CONFIG FOUND:")
        print(f"   Threads: {best_threads}")
        print(f"   Context: {best_context}")
        print(f"   Flags: {best_flags}")
        print(f"   Speed: {best_flag_speed:.1f} tok/s")
        print(f"{'='*60}")
        
        return optimal_config
    
    def get_optimal_flags(self) -> str:
        """Get optimal flags string for this model"""
        config = self.load_saved_config()
        if not config:
            config = self.tune()
        
        flags = f"-t {config['threads']} -c {config['context_size']}"
        if config.get("extra_flags"):
            flags += f" {config['extra_flags']}"
        return flags


def main():
    import argparse
    parser = argparse.ArgumentParser(description="GGUF Auto-Tuner")
    parser.add_argument("model", help="Path to GGUF model")
    parser.add_argument("--server", default="/home/nxyme/llama.cpp/build/bin/llama-server")
    parser.add_argument("--reset", action="store_true", help="Reset saved config")
    args = parser.parse_args()
    
    tuner = GGUF AutoTuner(args.model, args.server)
    
    if args.reset:
        if CONFIG_FILE.exists():
            os.remove(CONFIG_FILE)
            print("Config reset.")
        return
    
    config = tuner.tune()
    print(f"\nOptimal flags: {tuner.get_optimal_flags()}")


if __name__ == "__main__":
    main()
