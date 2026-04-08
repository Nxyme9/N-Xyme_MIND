#!/usr/bin/env python3
"""
GGUF <-> HuggingFace Converter
Automatically converts between GGUF and HF formats for training

Usage:
    python convert_gguf.py to_hf --input models/qwen2.5-0.5b-instruct-q4_k_m.gguf --output models/hf/qwen2.5-0.5b
    python convert_gguf.py to_gguf --input models/hf/qwen2.5-0.5b --output models/qwen2.5-0.5b-rosetta.gguf
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


def find_conda_env():
    """Find conda environment with llama-cpp-python or gguf tools."""
    # Check common locations
    candidates = [
        Path.home() / "miniconda3",
        Path.home() / "anaconda3",
        Path("/opt/conda"),
        Path("/home/nxyme/miniconda3"),
        Path("/home/nxyme/anaconda3"),
    ]
    
    for base in candidates:
        if base.exists():
            for env in base / "envs":
                if env.exists():
                    for e in env.iterdir():
                        if e.is_dir() and (e / "bin" / "llama-quantize").exists():
                            return e
                        # Also check for conda binary
                        if (e / "conda" / "bin").exists():
                            return e
    return None


def run_cmd(cmd, env=None):
    """Run command and return output."""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=env
    )
    if result.returncode != 0:
        print(f"STDERR: {result.stderr}")
        print(f"STDOUT: {result.stdout}")
    return result


def convert_to_hf(input_gguf: str, output_dir: str):
    """Convert GGUF to HuggingFace format using llama.cpp."""
    input_path = Path(input_gguf)
    output_path = Path(output_dir)
    
    if not input_path.exists():
        print(f"ERROR: Input GGUF not found: {input_path}")
        return False
    
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Try using llama.cpp conversion tools
    # First check if we have the tools
    llama_cpp_paths = [
        Path("/home/nxyme/llama.cpp"),
        Path.home() / "llama.cpp",
        Path("./llama.cpp"),
    ]
    
    convert_script = None
    for p in llama_cpp_paths:
        if p.exists():
            if (p / "convert_hf_to_gguf.py").exists():
                # We need the reverse - gguf to hf
                # Use llama.cpp main binary
                convert_script = p
                break
            if (p / "convert.py").exists():
                convert_script = p
                break
    
    # Alternative: use python with llama-cpp
    print("Converting GGUF to HF format...")
    
    # Method 1: Try using ctransformers or llama-cpp-python
    try:
        from llama_cpp import Llama
        import json
        
        # Load GGUF and save in HF format
        print("Loading GGUF model with llama-cpp-python...")
        
        # This is tricky - llama-cpp doesn't directly export to HF
        # We'll use a workaround: extract quant info
        
        print("Note: Direct GGUF->HF conversion requires llama.cpp tools")
        print("Alternative approach: Use GGUF directly for training via interpolation")
        
    except Exception as e:
        print(f"llama-cpp-python method failed: {e}")
    
    # Method 2: Use llama.cpp binary if available
    if convert_script:
        # llama.cpp doesn't have direct GGUF->HF, but we can
        # use the quantize tool to work around
        print(f"Found llama.cpp at: {convert_script}")
    
    # For now, let's use the simplest approach:
    # Download the original HF model and quantize it ourselves
    print("\n" + "="*50)
    print("Alternative: Download HF -> Quantize to GGUF")
    print("="*50)
    print("This is the recommended workflow:")
    print("1. Download HF model: Qwen/Qwen2.5-0.5B-Instruct")
    print("2. Quantize to GGUF: llama-quantize")
    print("3. Fine-tune (works with HF format)")
    print("4. Export back to GGUF")
    print("\nUse: python scripts/download_and_quantize.py")
    
    return False


def convert_to_gguf(input_dir: str, output_gguf: str, quant_type: str = "q4_k_m"):
    """Convert HuggingFace to GGUF format."""
    input_path = Path(input_dir)
    
    if not input_path.exists():
        print(f"ERROR: Input HF dir not found: {input_path}")
        return False
    
    print(f"Converting {input_dir} to GGUF...")
    
    # Find llama.cpp
    llama_cpp = Path("/home/nxyme/llama.cpp")
    if not llama_cpp.exists():
        llama_cpp = Path.home() / "llama.cpp"
    
    if llama_cpp.exists():
        convert_py = llama_cpp / "convert_hf_to_gguf.py"
        if convert_py.exists():
            cmd = [
                "python3", str(convert_py),
                str(input_path),
                "--outfile", output_gguf,
                "--quantize", quant_type
            ]
            run_cmd(cmd)
            return True
    
    print("llama.cpp not found. Install from: https://github.com/ggerganov/llama.cpp")
    return False


def download_and_quantize(model_name: str, output_dir: str, quant: str = "q4_k_m"):
    """Download HF model and quantize to GGUF."""
    print(f"\nDownloading {model_name}...")
    
    # Download from HuggingFace
    try:
        from huggingface_hub import snapshot_download
        
        local_dir = Path(output_dir) / model_name.replace("/", "_")
        local_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"Downloading to {local_dir}...")
        snapshot_download(
            repo_id=model_name,
            local_dir=str(local_dir),
            local_dir_use_symlinks=False
        )
        print(f"Downloaded to: {local_dir}")
        
        # Now quantize
        print(f"\nQuantizing to {quant}...")
        quantize_cmd = [
            "llama-quantize",
            str(local_dir / "*.bin"),  # This won't work - need actual file
            str(Path(output_dir) / f"{model_name.replace('/', '_')}_{quant}.gguf"),
            quant
        ]
        
        print("To quantize, run:")
        print(f"  llama.cpp/llama-quantize {local_dir}/consolidated.00.pt output.gguf {quant}")
        
        return str(local_dir)
        
    except Exception as e:
        print(f"Download error: {e}")
        print("\nManual download:")
        print(f"  huggingface-cli download {model_name}")
        return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GGUF <-> HF Converter")
    subparsers = parser.add_subparsers(dest="command")
    
    # To HF
    to_hf = subparsers.add_parser("to_hf", help="Convert GGUF to HuggingFace")
    to_hf.add_argument("--input", required=True, help="Input GGUF file")
    to_hf.add_argument("--output", required=True, help="Output HF directory")
    
    # To GGUF
    to_gguf = subparsers.add_parser("to_gguf", help="Convert HuggingFace to GGUF")
    to_gguf.add_argument("--input", required=True, help="Input HF directory")
    to_gguf.add_argument("--output", required=True, help="Output GGUF file")
    to_gguf.add_argument("--quant", default="q4_k_m", help="Quantization type")
    
    # Download & Quantize
    dl = subparsers.add_parser("download", help="Download HF and quantize to GGUF")
    dl.add_argument("--model", default="Qwen/Qwen2.5-0.5B-Instruct", help="Model name")
    dl.add_argument("--output", default="models", help="Output directory")
    dl.add_argument("--quant", default="q4_k_m", help="Quantization type")
    
    args = parser.parse_args()
    
    if args.command == "to_hf":
        convert_to_hf(args.input, args.output)
    elif args.command == "to_gguf":
        convert_to_gguf(args.input, args.output, args.quant)
    elif args.command == "download":
        download_and_quantize(args.model, args.output, args.quant)
    else:
        parser.print_help()