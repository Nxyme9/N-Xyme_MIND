#!/usr/bin/env python3
"""
Train Rosetta 0.5B - Exact copy of production trainer but for 0.5B
"""
import os
import sys
import signal
import json
import torch
from datetime import datetime

signal.signal(signal.SIGINT, signal.SIG_IGN)
signal.signal(signal.SIGTERM, signal.SIG_IGN)

from unsloth import FastLanguageModel, UnslothTrainer, UnslothTrainingArguments
from datasets import Dataset

CONFIG = {
    "model_path": "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/models/qwen2.5-0.5b-instruct",
    "output_dir": "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/nx_trainer/outputs/rosetta_0.5b",
    "data_file": "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/nx_trainer/data/v4_real.jsonl",
    "learning_rate": 1e-4,
    "num_epochs": 20,
    "batch_size": 2,
    "grad_accum": 1,
    "warmup_steps": 10,
    "max_seq_length": 1024,
    "save_steps": 50,
    "logging_steps": 25,
}

LOG_FILE = "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/nx_trainer/train_0.5b.log"

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def load_data(tokenizer):
    log("Loading training data...")
    texts = []
    total = 0
    skipped = 0
    
    with open(CONFIG["data_file"]) as f:
        for line in f:
            d = json.loads(line)
            try:
                if "messages" in d:
                    msgs = d.get("messages", [])
                    if len(msgs) >= 2 and msgs[0].get("role") == "user":
                        messages = msgs[:2]
                    else:
                        skipped += 1
                        continue
                elif "input" in d and "output" in d:
                    messages = [
                        {"role": "user", "content": d["input"]},
                        {"role": "assistant", "content": d["output"]},
                    ]
                else:
                    skipped += 1
                    continue
            except:
                skipped += 1
                continue
                
            text = tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=False
            )
            texts.append({"text": text})
            total += 1
    
    log(f"Loaded {total} examples, skipped {skipped}")
    return Dataset.from_list(texts)

def main():
    log("="*50)
    log("TRAINING ROSETTA 0.5B MODEL")
    log("="*50)
    
    if not torch.cuda.is_available():
        log("ERROR: No GPU!")
        sys.exit(1)
    
    log(f"GPU: {torch.cuda.get_device_name(0)}")
    log(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
    
    log(f"Loading model: {CONFIG['model_path']}")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=CONFIG["model_path"],
        max_seq_length=CONFIG["max_seq_length"],
        dtype=None,
        load_in_4bit=True,
        trust_remote_code=True,
    )
    
    log("Adding LoRA adapters...")
    model = FastLanguageModel.get_peft_model(
        model,
        r=16,
        lora_alpha=32,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        lora_dropout=0,
        bias="none",
    )
    
    dataset = load_data(tokenizer)
    
    training_args = UnslothTrainingArguments(
        per_device_train_batch_size=CONFIG["batch_size"],
        gradient_accumulation_steps=CONFIG["grad_accum"],
        warmup_steps=CONFIG["warmup_steps"],
        num_train_epochs=CONFIG["num_epochs"],
        learning_rate=CONFIG["learning_rate"],
        bf16=torch.cuda.is_bf16_supported(),
        logging_steps=CONFIG["logging_steps"],
        save_steps=CONFIG["save_steps"],
        optim="adamw_8bit",
        seed=42,
        output_dir=CONFIG["output_dir"],
        packing=True,
        dataloader_num_workers=0,
        report_to=["none"],
        max_grad_norm=1.0,
        remove_unused_columns=False,
    )
    
    log(f"Learning rate: {CONFIG['learning_rate']}")
    log(f"Epochs: {CONFIG['num_epochs']}")
    log(f"Batch size: {CONFIG['batch_size']}")
    log(f"bf16: {training_args.bf16}")
    
    log("Creating trainer...")
    trainer = UnslothTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        dataset_text_field="text",
        args=training_args,
    )
    
    log("Starting training...")
    trainer.train()
    
    log("Saving model...")
    model.save_pretrained(f"{CONFIG['output_dir']}/final")
    tokenizer.save_pretrained(f"{CONFIG['output_dir']}/final")
    
    log("="*50)
    log("TRAINING COMPLETE!")
    log("="*50)

if __name__ == "__main__":
    main()