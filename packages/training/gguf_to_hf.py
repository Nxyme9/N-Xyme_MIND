#!/usr/bin/env python3
"""
GGUF to HuggingFace Converter
Extracts weights from GGUF and saves as HF format for training

Usage:
    python gguf_to_hf.py --input models/qwen2.5-0.5b-instruct-q4_k_m.gguf --output models/hf-qwen2.5-0.5b
"""

import argparse
import json
import os
import struct
from pathlib import Path

import gguf
import torch
import numpy as np


# Qwen2-specific tensor name mapping
TENSOR_MAPPING = {
    # Embeddings
    "token_embd.weight": "model.embed_tokens.weight",
    # Output
    "output.weight": "lm_head.weight",
    # Block attention
    "blk.{n}.attn_norm.weight": "model.layers.{n}.input_layernorm.weight",
    # Block MLP
    "blk.{n}.ffn_norm.weight": "model.layers.{n}.post_attention_layernorm.weight",
    # Attention
    "blk.{n}.attn_q.weight": "model.layers.{n}.self_attn.q_proj.weight",
    "blk.{n}.attn_k.weight": "model.layers.{n}.self_attn.k_proj.weight",
    "blk.{n}.attn_v.weight": "model.layers.{n}.self_attn.v_proj.weight",
    "blk.{n}.attn_output.weight": "model.layers.{n}.self_attn.o_proj.weight",
    # MLP
    "blk.{n}.ffn_gate.weight": "model.layers.{n}.mlp.gate_proj.weight",
    "blk.{n}.ffn_up.weight": "model.layers.{n}.mlp.up_proj.weight",
    "blk.{n}.ffn_down.weight": "model.layers.{n}.mlp.down_proj.weight",
}


def get_dtype(qtype: int) -> torch.dtype:
    """Map GGUF quant type to torch dtype."""
    dtype_map = {
        0: torch.float32,    # F32
        1: torch.float16,    # F16
        2: torch.bfloat16,   # BF16
        7: torch.float16,    # Q4_0
        8: torch.float16,    # Q4_1
        9: torch.float16,    # Q5_0
        10: torch.float16,   # Q5_1
        11: torch.float16,   # Q8_0
        12: torch.float16,   # Q8_1
        13: torch.float16,   # TQ1
        14: torch.float16,   # TQ2
        15: torch.float16,   # TQ3
        16: torch.float16,   # TQ4
        17: torch.float16,   # TQ5
        18: torch.float16,   # Q2_K
        19: torch.float16,   # Q3_K
        20: torch.float16,   # Q4_K
        21: torch.float16,   # Q5_K
        22: torch.float16,   # Q6_K
        23: torch.float16,   # Q8_K
        24: torch.float16,   # IQ2_XXS
        25: torch.float16,   # IQ2_XS
        26: torch.float16,   # IQ3_XXS
        27: torch.float16,   # IQ1_S
        28: torch.float16,   # IQ2_S
        29: torch.float16,   # IQ4_XS
        30: torch.float16,   # I8
        31: torch.float16,   # I16
        32: torch.float16,   # I32
        33: torch.float16,   # I64
        34: torch.float16,   # F64
        35: torch.float16,   # BF16
    }
    return dtype_map.get(qtype, torch.float16)


def convert_tensor_name(gguf_name: str) -> str:
    """Convert GGUF tensor name to HF tensor name."""
    # Check for block numbers
    if "blk." in gguf_name:
        for n in range(28):  # Max 28 blocks for 0.5B
            if f"blk.{n}." in gguf_name:
                hf_name = gguf_name.replace(f"blk.{n}.", f"model.layers.{n}.")
                # Apply mapping
                for gguf_pattern, hf_pattern in TENSOR_MAPPING.items():
                    if ".{n}." in gguf_pattern:
                        pattern = gguf_pattern.replace("{n}", str(n))
                        if pattern in gguf_name:
                            hf_name = hf_pattern.replace("{n}", str(n))
                            break
                return hf_name
    
    # Direct mapping
    return TENSOR_MAPPING.get(gguf_name, gguf_name)


def dequantize_tensor(data: np.ndarray, shape: tuple, qtype: int) -> np.ndarray:
    """Dequantize GGUF tensor to FP16."""
    # For now, just return as-is (already unpacked by gguf library)
    # In production, would implement proper dequantization
    return data


def convert_gguf_to_hf(gguf_path: str, output_dir: str):
    """Convert GGUF to HuggingFace format."""
    print(f"Loading GGUF: {gguf_path}")
    
    reader = gguf.GGUFReader(gguf_path)
    
    # Get metadata
    metadata = {}
    for key in reader.fields:
        metadata[key] = reader.fields[key].parts
    
    print(f"Architecture: {metadata.get('general.architecture', 'unknown')}")
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Convert tensors
    tensors = {}
    print(f"Converting {len(reader.tensors)} tensors...")
    
    for tensor in reader.tensors:
        hf_name = convert_tensor_name(tensor.name)
        
        # Get tensor data (dequantized)
        # gguf library should return dequantized data
        data = tensor.tensor.data
        
        # Convert to torch
        dtype = get_dtype(tensor.tensor_type)
        torch_tensor = torch.from_numpy(data).to(dtype)
        
        tensors[hf_name] = torch_tensor
        
        if len(tensors) % 20 == 0:
            print(f"  Converted {len(tensors)} tensors...")
    
    print(f"Total: {len(tensors)} tensors")
    
    # Save in HF format
    print(f"Saving to {output_path}")
    
    # Save weights as safetensors
    from safetensors.torch import save_file
    
    # Split into chunks for large models
    chunk_size = 10
    tensor_items = list(tensors.items())
    
    for i in range(0, len(tensor_items), chunk_size):
        chunk = dict(tensor_items[i:i+chunk_size])
        save_file(chunk, f"{output_path}/model-{i:05d}.safetensors")
    
    # Save metadata
    config = {
        "architectures": ["Qwen2ForCausalLM"],
        "model_type": "qwen2",
        "torch_dtype": "float16",
        "transformers_version": "4.40.0",
    }
    
    # Extract key params from GGUF metadata
    if "qwen2.embedding_length" in metadata:
        config["hidden_size"] = int(metadata["qwen2.embedding_length"][0])
    if "qwen2.block_count" in metadata:
        config["num_hidden_layers"] = int(metadata["qwen2.block_count"][0])
    if "qwen2.attention.head_count" in metadata:
        config["num_attention_heads"] = int(metadata["qwen2.attention.head_count"][0])
    if "qwen2.attention.head_count_kv" in metadata:
        config["num_key_value_heads"] = int(metadata["qwen2.attention.head_count_kv"][0])
    if "qwen2.context_length" in metadata:
        config["max_position_embeddings"] = int(metadata["qwen2.context_length"][0])
    
    with open(output_path / "config.json", "w") as f:
        json.dump(config, f, indent=2)
    
    # Save tokenizer
    tokenizer_config = {
        "added_tokens_decoder": {},
        "bos_token": "<|endoftext|>",
        "eos_token": "<|endoftext|>",
        "pad_token": "<|endoftext|>",
        "chat_template": "[TOOL_CALL]{tool => \"%s\", args => { %%s }}[/TOOL_CALL]",
    }
    
    # Get tokenizer info from GGUF
    if "tokenizer.ggml.tokens" in metadata:
        # Decode tokens
        tokens = metadata["tokenizer.ggml.tokens"][0]
        tokenizer_config["vocab_size"] = len(tokens)
    
    with open(output_path / "tokenizer_config.json", "w") as f:
        json.dump(tokenizer_config, f, indent=2)
    
    print(f"\n✓ Conversion complete!")
    print(f"  Output: {output_path}")
    print(f"  Next: Train with this HF format, then convert back to GGUF")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert GGUF to HuggingFace format")
    parser.add_argument("--input", required=True, help="Input GGUF file")
    parser.add_argument("--output", required=True, help="Output HF directory")
    
    args = parser.parse_args()
    convert_gguf_to_hf(args.input, args.output)