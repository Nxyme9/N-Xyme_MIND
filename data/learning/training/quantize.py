"""
GGUF Export and Quantization for RosEnna Model.
Merges DoRA adapters with base model and exports to GGUF format.
"""

import os
import subprocess
import torch
from typing import Optional
from pathlib import Path


def merge_and_export(
    model,
    output_path: str,
    quantization: str = "q8_0",
    export_format: str = "hf",
) -> str:
    """
    Merge DoRA adapters with base model and export.

    Args:
        model: PEFT model with DoRA adapters
        output_path: Output file path
        quantization: Quantization type (q8_0, q4_0, etc.)
        export_format: Export format ("hf" for HuggingFace, "gguf" for GGUF)

    Returns:
        Path to exported model
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if export_format == "hf":
        # Export to HuggingFace format first
        hf_path = str(output_path).replace(".gguf", "-hf")
        _export_huggingface(model, hf_path)

        # Convert to GGUF
        if quantization:
            output_path = _convert_to_gguf(hf_path, str(output_path), quantization)

        return str(output_path)

    elif export_format == "gguf":
        # Direct GGUF export
        _export_huggingface(model, str(output_path).replace(".gguf", "-temp"))
        output_path = _convert_to_gguf(
            str(output_path).replace(".gguf", "-temp"),
            str(output_path),
            quantization
        )
        return str(output_path)

    else:
        raise ValueError(f"Unknown export format: {export_format}")


def _export_huggingface(model, output_path: str) -> None:
    """
    Export merged model to HuggingFace format.

    Args:
        model: PEFT model
        output_path: Output directory path
    """
    if hasattr(model, 'merge_and_unload'):
        # Merge adapters into base model
        merged_model = model.merge_and_unload()
    else:
        merged_model = model

    # Save as HuggingFace format
    merged_model.save_pretrained(output_path)

    # Save tokenizer
    if hasattr(model, 'tokenizer'):
        model.tokenizer.save_pretrained(output_path)

    print(f"Model exported to HuggingFace format: {output_path}")


def _convert_to_gguf(
    input_path: str,
    output_path: str,
    quantization: str = "q8_0",
) -> str:
    """
    Convert HuggingFace model to GGUF format using llama.cpp.

    Args:
        input_path: Input HuggingFace model path
        output_path: Output GGUF file path
        quantization: Quantization type

    Returns:
        Path to GGUF file
    """
    # Try to use llama.cpp convert script
    convert_script = _find_llama_cpp_convert()

    if convert_script is None:
        print("Warning: llama.cpp not found, saving in HuggingFace format only")
        return input_path

    # Run conversion
    try:
        cmd = [
            "python3",
            convert_script,
            input_path,
            "--outfile",
            output_path,
            "--outtype",
            quantization.replace("q", "").replace("_", "."),
        ]

        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,
        )

        if result.returncode != 0:
            print(f"Conversion failed: {result.stderr}")
            return input_path

        print(f"GGUF model saved: {output_path}")
        return output_path

    except subprocess.TimeoutExpired:
        print("Conversion timed out")
        return input_path
    except Exception as e:
        print(f"Conversion error: {e}")
        return input_path


def _find_llama_cpp_convert() -> Optional[str]:
    """
    Find llama.cpp convert script.

    Returns:
        Path to convert.py or None if not found
    """
    search_paths = [
        "/usr/local/bin/convert.py",
        "/usr/bin/convert.py",
        os.path.expanduser("~/llama.cpp/convert.py"),
        os.path.expanduser("~/ llama.cpp/convert.py"),
    ]

    # Also check if llama.cpp is in PATH
    try:
        result = subprocess.run(
            ["which", "llama-cli"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            # llama.cpp is installed
            pass
    except:
        pass

    for path in search_paths:
        if os.path.exists(path):
            return path

    # Check common locations
    common_dirs = [
        "/opt/llama.cpp",
        "/usr/local/share/llama.cpp",
        os.path.expanduser("~/code/llama.cpp"),
    ]

    for dir_path in common_dirs:
        convert_path = os.path.join(dir_path, "convert.py")
        if os.path.exists(convert_path):
            return convert_path

    return None


def quantize_gguf(
    input_path: str,
    output_path: str,
    quantization_type: str = "q8_0",
) -> str:
    """
    Quantize an existing GGUF model.

    Args:
        input_path: Input GGUF file path
        output_path: Output GGUF file path
        quantization_type: Target quantization type

    Returns:
        Path to quantized GGUF file
    """
    # Try to find llama.cpp quantize binary
    quantize_bin = _find_llama_cpp_quantize()

    if quantize_bin is None:
        print("Warning: llama.cpp quantize not found")
        return input_path

    try:
        cmd = [
            quantize_bin,
            input_path,
            output_path,
            quantization_type,
        ]

        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
        )

        if result.returncode != 0:
            print(f"Quantization failed: {result.stderr}")
            return input_path

        print(f"Quantized model saved: {output_path}")
        return output_path

    except Exception as e:
        print(f"Quantization error: {e}")
        return input_path


def _find_llama_cpp_quantize() -> Optional[str]:
    """Find llama.cpp quantize binary."""
    search_paths = [
        "/usr/local/bin/quantize",
        "/usr/bin/quantize",
    ]

    for path in search_paths:
        if os.path.exists(path):
            return path

    return None


def export_for_inference(
    model,
    output_dir: str,
    quantization: str = "q8_0",
) -> dict:
    """
    Complete export pipeline for inference.

    Args:
        model: Trained model
        output_dir: Output directory
        quantization: Quantization type

    Returns:
        Dictionary with export info
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Export to HuggingFace format
    hf_path = output_dir / "model-hf"
    _export_huggingface(model, str(hf_path))

    # Convert to GGUF
    gguf_path = output_dir / f"model-{quantization}.gguf"

    if _find_llama_cpp_convert() is not None:
        gguf_path = Path(_convert_to_gguf(str(hf_path), str(gguf_path), quantization))
    else:
        print("GGUF conversion skipped - llama.cpp not found")

    return {
        "hf_path": str(hf_path),
        "gguf_path": str(gguf_path),
        "quantization": quantization,
    }


# Standalone functions for CLI usage
def main():
    """CLI entry point for export."""
    import argparse

    parser = argparse.ArgumentParser(description="Export RosEnna model to GGUF")
    parser.add_argument("--input", required=True, help="Input model path (HuggingFace or checkpoint)")
    parser.add_argument("--output", required=True, help="Output GGUF path")
    parser.add_argument("--quantization", default="q8_0", help="Quantization type")
    parser.add_argument("--merge", action="store_true", help="Merge adapters first")

    args = parser.parse_args()

    # Load model if checkpoint provided
    if os.path.exists(args.input):
        from model.encoder import RosEnnaEncoder
        model = RosEnnaEncoder()
        if args.merge:
            model.load_adapters(args.input)
        else:
            model.load_adapters(args.input)

        merge_and_export(model, args.output, args.quantization)
    else:
        print(f"Input path not found: {args.input}")


if __name__ == "__main__":
    main()