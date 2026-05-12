"""Trainer for Rosetta Stone - Optimized fine-tuning for tool call translation.

Optimizations:
- Unsloth: 2x faster, 70% less VRAM
- 4-bit quantization: Minimal quality loss
- AdamW 8-bit: 50% less memory
- Gradient checkpointing: Save VRAM
- Flash Attention: Speed boost
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional

from nx_trainer.config import (
    LoRAConfig,
    GGUFExportConfig,
    MODEL_CONFIGS,
    OllamaConfig,
    TrainingConfig,
)


class Trainer:
    """High-performance trainer using Unsloth for tool-call fine-tuning.

    Supports:
    - Unsloth: 2x faster, 70% less VRAM (RECOMMENDED)
    - GGUF export: For llama-server (no Ollama dependency)
    - Multi-model: Qwen2.5, Llama3.2, etc.
    """

    def __init__(
        self,
        lora_config: Optional[LoRAConfig] = None,
        training_config: Optional[TrainingConfig] = None,
        ollama_config: Optional[OllamaConfig] = None,
    ):
        self.lora_config = lora_config or LoRAConfig()
        self.training_config = training_config or TrainingConfig()
        self.ollama_config = ollama_config or OllamaConfig()

    @staticmethod
    def get_model_config(model_key: str) -> Dict[str, Any]:
        """Get optimal config for a model."""
        if model_key not in MODEL_CONFIGS:
            raise ValueError(f"Unknown model: {model_key}. Available: {list(MODEL_CONFIGS.keys())}")
        return MODEL_CONFIGS[model_key]

    def train_with_unsloth(
        self,
        data_path: Path,
        output_dir: Optional[Path] = None,
    ) -> bool:
        """Train using Unsloth - 2x faster, 70% less VRAM."""
        try:
            import unsloth
            # Must import unsloth first for optimizations
        except ImportError:
            print("ERROR: Unsloth not installed")
            print("  Install: pip install unsloth")
            return False

        from unsloth import FastLanguageModel
        import torch
        from trl import SFTTrainer
        from transformers import TrainingArguments

        # Load training data
        with open(data_path) as f:
            data = [json.loads(line) for line in f]
        print(f"Loaded {len(data)} training examples")

        # Auto-detect dtype
        dtype = None
        if torch.cuda.is_available():
            dtype = "bfloat16" if torch.cuda.is_bf16_supported() else "float16"
        print(f"Using dtype: {dtype or 'float32'}")

        # Load base model
        print(f"Loading model: {self.training_config.model_name}")
        model, tokenizer = FastLanguageModel.from_pretrained(
            model_name=self.training_config.model_name,
            max_seq_length=self.training_config.max_seq_length,
            dtype=dtype,
            load_in_4bit=self.training_config.load_in_4bit,
        )

        # Add LoRA adapters (NOTE: task_type is now handled automatically by Unsloth)
        print(
            f"LoRA: r={self.lora_config.r}, alpha={self.lora_config.alpha}, use_dora={self.lora_config.use_dora}"
        )
        model = FastLanguageModel.get_peft_model(
            model,
            r=self.lora_config.r,
            target_modules=self.lora_config.target_modules,
            lora_alpha=self.lora_config.alpha,
            lora_dropout=self.lora_config.dropout,
            bias=self.lora_config.bias,
            # Unsloth-specific optimizations
            use_gradient_checkpointing="unsloth",
            use_rslora=self.lora_config.use_rslora
            if hasattr(self.lora_config, "use_rslora")
            else False,
            use_dora=self.lora_config.use_dora,
        )

        # PEFT best practices: enable input gradients BEFORE gradient checkpointing
        # This is required for gradient checkpointing to work properly with LoRA
        if hasattr(model, "enable_input_require_grads"):
            model.enable_input_require_grads()
        else:
            # Fallback for older versions
            def make_inputs_require_grad(module, input, output):
                output.requires_grad_(True)

            model.get_input_embeddings().register_forward_hook(make_inputs_require_grad)

        # Gradient checkpointing must be enabled AFTER get_peft_model() and enable_input_require_grads()
        # This saves ~30% VRAM at cost of ~20% slower training
        if hasattr(model, "gradient_checkpointing_enable"):
            model.gradient_checkpointing_enable()

        # Format data using Qwen's chat template - CRITICAL for instruction tuning
        # Must use apply_chat_template for proper format with <|im_start|>user/assistant<|im_end|> tokens
        training_data = []
        for item in data:
            messages = [
                {"role": "user", "content": item["input"]},
                {"role": "assistant", "content": item["output"]},
            ]
            text = tokenizer.apply_chat_template(messages, tokenize=False)
            training_data.append({"text": text})

        # Optimized training arguments
        output_dir = output_dir or Path(self.training_config.output_dir)

        training_args = TrainingArguments(
            per_device_train_batch_size=self.training_config.per_device_train_batch_size,
            gradient_accumulation_steps=self.training_config.gradient_accumulation_steps,
            warmup_steps=self.training_config.warmup_steps,
            num_train_epochs=self.training_config.num_train_epochs,
            learning_rate=self.training_config.learning_rate,
            fp16=torch.cuda.is_bf16_supported() if torch.cuda.is_available() else False,
            bf16=torch.cuda.is_bf16_supported() if torch.cuda.is_available() else False,
            logging_steps=self.training_config.logging_steps,
            optim=self.training_config.optim,
            weight_decay=self.training_config.weight_decay,
            lr_scheduler_type=self.training_config.lr_scheduler_type,
            seed=self.training_config.seed,
            output_dir=str(output_dir),
            report_to="none",
            save_strategy="epoch",
            save_steps=999999,
            push_to_hub=False,
            hub_model_id=None,
        )

        print(f"Training {self.training_config.num_train_epochs} epochs...")

        trainer = SFTTrainer(
            model=model,
            tokenizer=tokenizer,
            train_dataset=training_data,
            dataset_text_field="text",
            max_seq_length=self.training_config.max_seq_length,
            args=training_args,
        )

        trainer.train()

        # Save LoRA adapters
        output_path = output_dir / "rosetta-lora"
        model.save_pretrained(str(output_path))
        tokenizer.save_pretrained(str(output_path))
        print(f"✓ Saved to: {output_path}")

        return True

    def export_to_gguf(
        self,
        lora_path: Path,
        output_path: Optional[Path] = None,
        config: Optional[GGUFExportConfig] = None,
    ) -> bool:
        """Export trained LoRA to GGUF for llama-server.

        Uses llama.cpp for real GGUF conversion if available,
        otherwise falls back to Ollama Modelfile.
        """
        config = config or GGUFExportConfig()
        output_path = (
            output_path or Path(config.output_dir) / f"rosetta-{config.quantize_method}.gguf"
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)

        print(f"Exporting to GGUF: {output_path}")

        # Try llama.cpp conversion first
        if self._export_with_llama_cpp(lora_path, output_path, config):
            print(f"✓ GGUF export completed: {output_path}")
            return True

        # Fallback: create Ollama Modelfile
        print("NOTE: llama.cpp not found. Using Modelfile fallback.")

        modelfile = f"""FROM {config.base_model_name}
ADAPTER {lora_path}

SYSTEM
You are a tool call translator. Convert user requests to MCP tool calls.
Format: [TOOL_CALL]{{tool => "tool_name", args => {{ --arg "value" }}}}[/TOOL_CALL]
"""

        modelfile_path = output_path.with_suffix(".Modelfile")
        with open(modelfile_path, "w") as f:
            f.write(modelfile)

        print(f"✓ Created Modelfile: {modelfile_path}")
        return True

    def _export_with_llama_cpp(
        self,
        lora_path: Path,
        output_path: Path,
        config: GGUFExportConfig,
    ) -> bool:
        """Export using llama.cpp convert_lora_to_gguf.py script.

        Requires llama.cpp to be installed and available.
        This script merges LoRA adapters with base model and exports to GGUF.
        """
        import shutil

        # Check for llama.cpp convert_lora_to_gguf.py script
        llama_cpp_script = shutil.which("convert_lora_to_gguf.py")
        if not llama_cpp_script:
            # Try common locations
            possible_paths = [
                Path.home() / "llama.cpp" / "convert_lora_to_gguf.py",
                Path("/usr/local/bin/convert_lora_to_gguf.py"),
                Path("/usr/bin/convert_lora_to_gguf.py"),
            ]
            for p in possible_paths:
                if p.exists():
                    llama_cpp_script = str(p)
                    break

        if not llama_cpp_script:
            return False

        print(f"Using llama.cpp: {llama_cpp_script}")

        # Build base model path for conversion
        base_model = config.base_model_name or "Qwen/Qwen2.5-0.5B-Instruct"

        # Run conversion using convert_lora_to_gguf.py
        import subprocess

        cmd = [
            "python3",
            llama_cpp_script,
            str(lora_path),
            "--outfile",
            str(output_path),
            "--outtype",
            config.quantize_method,
            "--base-model-id",
            base_model,
        ]

        print(f"Running: {' '.join(cmd)}")

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            if result.returncode == 0:
                print(f"✓ GGUF export successful")
                return True
            else:
                print(f"llama.cpp export failed: {result.stderr}")
                if result.stdout:
                    print(f"stdout: {result.stdout}")
                return False
        except subprocess.TimeoutExpired:
            print("llama.cpp export timed out (6 min limit)")
            return False
        except Exception as e:
            print(f"llama.cpp export error: {e}")
            return False

    def train_with_ollama(
        self,
        data_path: Path,
        output_path: Optional[Path] = None,
    ) -> bool:
        """Train using Ollama via Modelfile generation.

        This creates an Ollama Modelfile with the training examples embedded
        as system prompt, which serves as a form of few-shot learning.

        Args:
            data_path: Path to training data JSONL file.
            output_path: Path to save the Modelfile.

        Returns:
            True if Modelfile was created successfully.
        """
        # Load training data
        with open(data_path) as f:
            data = [json.loads(line) for line in f]

        print(f"Loaded {len(data)} training examples")

        # Sample examples for the system prompt (limit to 20 to keep it manageable)
        sample_examples = data[:20]

        # Build examples section
        examples_text = "\n".join(
            f'- "{item["input"]}" → {item["output"]}' for item in sample_examples
        )

        # Build available tools section
        tools_text = """Available tools:
- memory_search: Search memory for information
- memory_write: Write to memory
- athena_smart_search: Search knowledge base
- read_file: Read file contents
- write_file: Write content to file
- list_directory: List directory contents
- git_status: Show git status
- git_log: Show commit history
- git_diff: Show differences
- github_list_issues: List GitHub issues
- fetch_url: Fetch web content
- context7_query_docs: Query documentation
- sequential_thinking: Chain of thought reasoning
- get_active_context: Get current context
- get_health: Check system health
- browser_navigate: Navigate browser
- route_task: Route task to appropriate agent"""

        # Create Modelfile content
        modelfile = f"""FROM {self.ollama_config.model_name}

SYSTEM
You are a Rosetta Stone tool call translator. Your job is to convert simple user requests
into proper MCP tool calls.

Format: [TOOL_CALL]{{tool => "tool_name", args => {{ --arg "value" }}}}[/TOOL_CALL]

Examples:
{examples_text}

{tools_text}

Instructions:
1. Convert user request to tool call format
2. Use [TOOL_CALL]...[/TOOL_CALL] wrapper
3. Be specific with arguments
4. If no tool needed, respond with text"""

        # Save Modelfile
        output_path = output_path or Path("rosetta.Modelfile")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            f.write(modelfile)

        print(f"Created Modelfile: {output_path}")
        print("\nTo train:")
        print(f"  1. ollama create rosetta -f {output_path}")
        print("  2. ollama run rosetta")
        print("\nThen test with:")
        print('  ollama run rosetta "search memory for security"')

        return True

    def train(
        self,
        data_path: Path,
        method: str = "unsloth",
        output_dir: Optional[Path] = None,
    ) -> bool:
        """Train the model using the specified method.

        Args:
            data_path: Path to training data JSONL file.
            method: Training method ("unsloth" or "ollama").
            output_dir: Output directory for trained model/Modelfile.

        Returns:
            True if training succeeded, False otherwise.
        """
        if method == "unsloth":
            return self.train_with_unsloth(data_path, output_dir)
        elif method == "ollama":
            modelfile_path = (output_dir or Path(".")) / "rosetta.Modelfile"
            return self.train_with_ollama(data_path, modelfile_path)
        else:
            print(f"ERROR: Unknown training method: {method}")
            return False

    @staticmethod
    def check_unsloth_available() -> bool:
        """Check if Unsloth is installed and available.

        Returns:
            True if Unsloth is available, False otherwise.
        """
        try:
            import unsloth

            return True
        except ImportError:
            return False

    @staticmethod
    def check_ollama_available() -> bool:
        """Check if Ollama is available on the system.

        Returns:
            True if Ollama CLI is available, False otherwise.
        """
        import shutil

        return shutil.which("ollama") is not None
