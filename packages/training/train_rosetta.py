#!/usr/bin/env python3
"""
Rosetta Stone Fine-tuning (No TRL - pure PEFT + Transformers)
Fine-tunes Qwen2.5-0.5B on tool call translation data

Usage:
    python train_rosetta.py --data datasets/rosetta_training.jsonl --output models/rosetta-lora
"""

import json
import os
import sys
import argparse
from pathlib import Path
from typing import List, Dict
import math

import torch
from torch.utils.data import Dataset as TorchDataset, DataLoader
from transformers import (
    AutoTokenizer, 
    AutoModelForCausalLM,
    get_cosine_schedule_with_warmup
)
from peft import LoraConfig, get_peft_model, TaskType


# Config
BASE_MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
OUTPUT_DIR = Path(__file__).parent / "models" / "rosetta-lora"


class RosettaDataset(TorchDataset):
    """Custom dataset for Rosetta training."""
    
    def __init__(self, data_path: str, tokenizer, max_length: int = 512):
        self.data = []
        self.tokenizer = tokenizer
        self.max_length = max_length
        
        # Load data
        with open(data_path, 'r') as f:
            for line in f:
                item = json.loads(line.strip())
                self.data.append(item)
        
        # Format template
        self.template = """<|im_start|>user
{input}<|im_end|>
<|im_start|>assistant
{output}<|im_end|>"""
    
    def __len__(self):
        return len(self.data)
    
    def __getitem__(self, idx):
        item = self.data[idx]
        
        # Format with chat template
        text = self.template.format(
            input=item["input"],
            output=item["output"]
        )
        
        # Tokenize
        encoding = self.tokenizer(
            text,
            max_length=self.max_length,
            padding="max_length",
            truncation=True,
            return_tensors="pt"
        )
        
        # Input IDs and labels (shifted for causal LM)
        input_ids = encoding["input_ids"].squeeze()
        labels = input_ids.clone()
        
        return {
            "input_ids": input_ids,
            "labels": labels
        }


def setup_model():
    """Load base model and tokenizer."""
    print(f"Loading base model: {BASE_MODEL}")
    
    tokenizer = AutoTokenizer.from_pretrained(
        BASE_MODEL,
        trust_remote_code=True,
        padding_side="right"
    )
    
    # Ensure pad token is set
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        trust_remote_code=True,
        torch_dtype=torch.float16,
        device_map="auto",
        offload_folder="/tmp/offload"
    )
    
    # Resize embeddings
    model.resize_token_embeddings(len(tokenizer))
    
    return model, tokenizer


def setup_lora(model):
    """Configure and apply LoRA."""
    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=16,              # LoRA rank
        lora_alpha=32,
        lora_dropout=0.1,
        target_modules=[
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj"
        ],
        bias="none",
        inference_mode=False
    )
    
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()
    
    return model


def train(
    data_path: str,
    output_dir: str,
    epochs: int = 3,
    batch_size: int = 4,
    learning_rate: float = 2e-4,
    max_seq_length: int = 512
):
    """Main training function."""
    print("\n" + "="*50)
    print("Rosetta Stone Fine-tuning (PEFT + Transformers)")
    print("="*50)
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Load model and tokenizer
    model, tokenizer = setup_model()
    
    # Apply LoRA
    model = setup_lora(model)
    
    # Create dataset and dataloader
    dataset = RosettaDataset(data_path, tokenizer, max_seq_length)
    dataloader = DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=True,
        drop_last=True
    )
    
    print(f"\nDataset: {len(dataset)} examples")
    print(f"Batches: {len(dataloader)} per epoch")
    
    # Optimizer and scheduler
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=learning_rate,
        weight_decay=0.01
    )
    
    total_steps = len(dataloader) * epochs
    scheduler = get_cosine_schedule_with_warmup(
        optimizer,
        num_warmup_steps=int(total_steps * 0.1),
        num_training_steps=total_steps
    )
    
    # Training loop
    model.train()
    
    for epoch in range(epochs):
        total_loss = 0
        
        for batch_idx, batch in enumerate(dataloader):
            # Move to device
            input_ids = batch["input_ids"].to(model.device)
            labels = batch["labels"].to(model.device)
            
            # Forward pass
            outputs = model(
                input_ids=input_ids,
                labels=labels
            )
            
            loss = outputs.loss
            
            # Backward
            loss.backward()
            optimizer.step()
            scheduler.step()
            optimizer.zero_grad()
            
            total_loss += loss.item()
            
            # Logging
            if batch_idx % 10 == 0:
                print(f"Epoch {epoch+1}/{epochs} | Batch {batch_idx}/{len(dataloader)} | Loss: {loss.item():.4f}")
        
        avg_loss = total_loss / len(dataloader)
        perplexity = math.exp(avg_loss)
        print(f"\nEpoch {epoch+1} Complete | Avg Loss: {avg_loss:.4f} | Perplexity: {perplexity:.2f}")
    
    # Save model
    print(f"\nSaving LoRA adapters to {output_path}")
    model.save_pretrained(str(output_path))
    tokenizer.save_pretrained(str(output_path))
    
    print("\n" + "="*50)
    print("Training Complete!")
    print(f"LoRA saved to: {output_path}")
    print("="*50)
    
    return str(output_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fine-tune Rosetta Stone model")
    parser.add_argument("--data", type=str, default="datasets/rosetta_training.jsonl",
                        help="Path to training data JSONL")
    parser.add_argument("--output", type=str, default="models/rosetta-lora",
                        help="Output directory for LoRA adapters")
    parser.add_argument("--epochs", type=int, default=3,
                        help="Number of training epochs")
    parser.add_argument("--batch", type=int, default=4,
                        help="Batch size")
    parser.add_argument("--lr", type=float, default=2e-4,
                        help="Learning rate")
    
    args = parser.parse_args()
    
    train(
        data_path=args.data,
        output_dir=args.output,
        epochs=args.epochs,
        batch_size=args.batch,
        learning_rate=args.lr
    )