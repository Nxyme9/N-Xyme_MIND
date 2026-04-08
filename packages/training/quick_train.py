#!/usr/bin/env python3
"""Quick Rosetta Training - minimal version for fast training"""

import json
import os
import torch
from torch.utils.data import Dataset, DataLoader
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import LoraConfig, get_peft_model, TaskType

# Config
MODEL_ID = "Qwen/Qwen2.5-0.5B-Instruct"
DATA_FILE = "datasets/rosetta_train_qwen.jsonl"
EPOCHS = 3
BATCH_SIZE = 4
LR = 2e-4
MAX_LEN = 256


# Dataset
class QwenDataset(Dataset):
    def __init__(self, path, tokenizer):
        self.data = []
        self.tokenizer = tokenizer
        with open(path, "r") as f:
            for line in f:
                item = json.loads(line)
                self.data.append(item["text"])

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        result = self.tokenizer(
            self.data[idx],
            max_length=MAX_LEN,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )
        # Return only what we need
        return {
            "input_ids": result["input_ids"].squeeze(0),
            "labels": result["input_ids"].squeeze(0),
        }


def main():
    print("Loading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=True)
    tokenizer.pad_token = tokenizer.eos_token

    print("Loading model...")
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        trust_remote_code=True,
        torch_dtype=torch.float16,
        device_map="auto",
        _attn_implementation="eager",
    )

    # LoRA
    lora = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=16,
        lora_alpha=32,
        target_modules=[
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
        ],
    )
    model = get_peft_model(model, lora)
    model.print_trainable_parameters()

    # Data
    dataset = QwenDataset(DATA_FILE, tokenizer)
    loader = DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=True)

    # Train
    model.train()
    optimizer = torch.optim.AdamW(model.parameters(), lr=LR)

    print(
        f"\nTraining: {len(dataset)} examples, {len(loader)} batches/epoch, {EPOCHS} epochs"
    )
    for epoch in range(EPOCHS):
        total_loss = 0
        for i, batch in enumerate(loader):
            inputs = {
                k: v.to(model.device) for k, v in batch.items() if k != "attention_mask"
            }
            outputs = model(**inputs)
            loss = outputs.loss
            loss.backward()
            optimizer.step()
            optimizer.zero_grad()
            total_loss += loss.item()
            if i % 10 == 0:
                print(
                    f"  Epoch {epoch + 1}, Batch {i}/{len(loader)}, Loss: {loss.item():.4f}"
                )
        print(f"Epoch {epoch + 1} done. Avg loss: {total_loss / len(loader):.4f}")

    # Save
    output_dir = "models/rosetta-lora"
    model.save_pretrained(output_dir)
    print(f"\nSaved LoRA to {output_dir}")


if __name__ == "__main__":
    main()
