"""ORPO (Odds Ratio Preference Optimization) trainer for nx_trainer.

ORPO is a newer preference optimization method (2024) that:
- Does NOT require a reference model (unlike DPO)
- Uses odds ratio loss for direct preference learning
- More memory efficient than DPO/GRPO
- Works well with single model

Paper: https://arxiv.org/abs/2403.07691

Key differences from DPO:
- No reference model needed → ~50% less VRAM
- Uses odds ratio loss directly
- Can be combined with SFT
"""

import json
import torch
import torch.nn as nn
import torch.nn.functional as F
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from transformers import (
    PreTrainedModel,
    PreTrainedTokenizerBase,
)
from trl.trainer.dpo_trainer import DPOTrainer


@dataclass
class ORPOConfig:
    """Configuration for ORPO training.

    Args:
        beta: Scaling factor for odds ratio loss (default: 0.1)
        lambda_: Interpolation between SFT and ORPO loss (default: 0.5)
        loss_type: Type of loss ("odds_ratio", "sigmoid", "hinge")
        label_smoothing: Label smoothing for SFT loss (default: 0.0)
        gradient_accumulation_steps: Gradient accumulation steps
        per_device_train_batch_size: Batch size per device
        learning_rate: Learning rate
        num_train_epochs: Number of training epochs
        max_seq_length: Maximum sequence length
        warmup_ratio: Warmup ratio
        logging_steps: Logging steps
        save_steps: Save checkpoint every N steps
        output_dir: Output directory
        fp16: Use FP16
        bf16: Use BF16
        logging_dir: Logging directory
        optim: Optimizer
        weight_decay: Weight decay
        lr_scheduler_type: LR scheduler type
        seed: Random seed
    """

    # Loss parameters
    beta: float = field(default=0.1)
    lambda_: float = field(default=0.5)
    loss_type: str = field(default="odds_ratio")
    label_smoothing: float = field(default=0.0)

    # Training arguments (mirrors TrainingArguments)
    gradient_accumulation_steps: int = field(default=1)
    per_device_train_batch_size: int = field(default=4)
    learning_rate: float = field(default=2e-5)
    num_train_epochs: int = field(default=3)
    max_seq_length: int = field(default=512)
    warmup_ratio: float = field(default=0.1)
    logging_steps: int = field(default=10)
    save_steps: int = field(default=500)
    output_dir: str = field(default="outputs/orpo")
    fp16: bool = field(default=False)
    bf16: bool = field(default=True)
    logging_dir: Optional[str] = field(default=None)
    optim: str = field(default="adamw_8bit")
    weight_decay: float = field(default=0.01)
    lr_scheduler_type: str = field(default="cosine")
    seed: int = field(default=42)

    # Model arguments
    model_name_or_path: str = field(default=None)
    trust_remote_code: bool = field(default=True)


class ORPOTrainer:
    """ORPO Trainer - Memory-efficient preference optimization.

    ORPO combines SFT loss with odds ratio loss for direct preference learning.
    Unlike DPO, it doesn't need a reference model.

    Advantages:
    - No reference model needed → ~50% less VRAM
    - Simpler implementation than GRPO/DPO
    - Can be combined with SFT training

    Usage:
        trainer = ORPOTrainer(
            model=model,
            tokenizer=tokenizer,
            config=ORPOConfig(beta=0.1, lambda_=0.5),
        )
        trainer.train(preference_dataset)
    """

    def __init__(
        self,
        model: PreTrainedModel,
        tokenizer: PreTrainedTokenizerBase,
        config: Optional[ORPOConfig] = None,
        train_dataset: Optional[Any] = None,
        eval_dataset: Optional[Any] = None,
        data_collator: Optional[Callable] = None,
    ):
        self.model = model
        self.tokenizer = tokenizer
        self.config = config or ORPOConfig()
        self.train_dataset = train_dataset
        self.eval_dataset = eval_dataset
        self.data_collator = data_collator

        # Device setup
        self.device = next(model.parameters()).device
        self.is_distributed = False

        # Initialize loss computation
        self.loss_fct = nn.CrossEntropyLoss(label_smoothing=self.config.label_smoothing)

    def compute_loss(
        self,
        model: PreTrainedModel,
        batch: Dict[str, torch.Tensor],
        return_logits: bool = False,
    ) -> Union[torch.Tensor, Tuple[torch.Tensor, torch.Tensor]]:
        """Compute ORPO loss.

        ORPO loss = SFT loss + beta * Odds Ratio loss

        The odds ratio loss directly optimizes the probability ratio
        between preferred and dispreferred responses.
        """
        # Unpack batch
        prompt_ids = batch["prompt_input_ids"]
        prompt_mask = batch.get("prompt_attention_mask")
        chosen_ids = batch["chosen_input_ids"]
        chosen_mask = batch.get("chosen_attention_mask")
        rejected_ids = batch["rejected_input_ids"]
        rejected_mask = batch.get("rejected_attention_mask")

        # Compute log probabilities for chosen and rejected
        chosen_logits = self._get_log_probs(model, chosen_ids, chosen_mask)
        rejected_logits = self._get_log_probs(model, rejected_ids, rejected_mask)

        # ORPO odds ratio loss
        if self.config.loss_type == "odds_ratio":
            # Standard odds ratio loss
            # log(sigmoid(chosen - rejected)) or equivalently
            # -log(1 + exp(rejected - chosen))
            odds_ratio_loss = -F.logsigmoid(chosen_logits - rejected_logits).mean()
        elif self.config.loss_type == "sigmoid":
            # Sigmoid loss
            sigmoid_loss = F.binary_cross_entropy_with_logits(
                chosen_logits - rejected_logits,
                torch.ones_like(chosen_logits),
            )
            odds_ratio_loss = sigmoid_loss
        elif self.config.loss_type == "hinge":
            # Hinge loss
            hinge_loss = F.relu(rejected_logits - chosen_logits + 1).mean()
            odds_ratio_loss = hinge_loss
        else:
            raise ValueError(f"Unknown loss type: {self.config.loss_type}")

        # SFT loss (optional, controlled by lambda_)
        if self.config.lambda_ < 1.0:
            # Compute SFT loss on chosen responses
            sft_loss = self._compute_sft_loss(model, chosen_ids, chosen_mask)
        else:
            sft_loss = torch.tensor(0.0, device=self.device)

        # Combined loss
        # total_loss = (1 - lambda_) * sft_loss + lambda_ * beta * odds_ratio_loss
        total_loss = (
            1 - self.config.lambda_
        ) * sft_loss + self.config.lambda_ * self.config.beta * odds_ratio_loss

        if return_logits:
            return total_loss, (chosen_logits.mean(), rejected_logits.mean())
        return total_loss

    def _get_log_probs(
        self,
        model: PreTrainedModel,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor,
    ) -> torch.Tensor:
        """Get log probabilities for the response tokens only."""
        # Forward pass
        outputs = model(
            input_ids=input_ids,
            attention_mask=attention_mask,
        )

        # Get logits and compute log probabilities
        logits = outputs.logits  # [batch, seq_len, vocab]

        # Shift for causal language modeling
        shift_logits = logits[..., :-1, :].contiguous()
        shift_labels = input_ids[..., 1:].contiguous()
        shift_attention = attention_mask[..., 1:].contiguous()

        # Compute log probabilities
        log_probs = F.log_softmax(shift_logits, dim=-1)

        # Gather log probs for labels
        # For each position, get the log prob of the actual token
        gather_indices = shift_labels.unsqueeze(-1)  # [batch, seq_len, 1]
        gathered_log_probs = log_probs.gather(-1, gather_indices).squeeze(-1)  # [batch, seq_len]

        # Mask and sum
        masked_log_probs = gathered_log_probs * shift_attention
        log_prob_sum = masked_log_probs.sum(dim=-1)  # [batch]

        # Return mean log prob per sample
        return log_prob_sum / shift_attention.sum(dim=-1).clamp(min=1)

    def _compute_sft_loss(
        self,
        model: PreTrainedModel,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor,
    ) -> torch.Tensor:
        """Compute standard SFT loss on chosen responses."""
        shift_logits = model(
            input_ids=input_ids,
            attention_mask=attention_mask,
        ).logits[..., :-1, :]
        shift_labels = input_ids[..., 1:]

        # Compute cross entropy
        loss = self.loss_fct(
            shift_logits.view(-1, shift_logits.size(-1)),
            shift_labels.view(-1),
        )
        return loss

    def train(
        self,
        output_dir: Optional[str] = None,
        resume_from_checkpoint: Optional[str] = None,
        show_progress: bool = True,
    ):
        """Train the model using ORPO."""
        from transformers import Trainer, TrainingArguments

        output_dir = output_dir or self.config.output_dir

        # Build training arguments
        training_args = TrainingArguments(
            output_dir=output_dir,
            per_device_train_batch_size=self.config.per_device_train_batch_size,
            gradient_accumulation_steps=self.config.gradient_accumulation_steps,
            learning_rate=self.config.learning_rate,
            num_train_epochs=self.config.num_train_epochs,
            max_seq_length=self.config.max_seq_length,
            warmup_ratio=self.config.warmup_ratio,
            logging_steps=self.config.logging_steps,
            save_steps=self.config.save_steps,
            fp16=self.config.fp16,
            bf16=self.config.bf16,
            optim=self.config.optim,
            weight_decay=self.config.weight_decay,
            lr_scheduler_type=self.config.lr_scheduler_type,
            seed=self.config.seed,
            save_total_limit=3,
            remove_unused_columns=False,
            label_names=["chosen_input_ids", "rejected_input_ids"],
            report_to="none",
        )

        # Create custom trainer that uses ORPO loss
        class ORPOTransformersTrainer(Trainer):
            def __init__(self, *args, orpo_trainer_ref=None, **kwargs):
                super().__init__(*args, **kwargs)
                self.orpo_trainer_ref = orpo_trainer_ref

            def compute_loss(self, model, inputs, return_logits=False, **kwargs):
                return self.orpo_trainer_ref.compute_loss(
                    model, inputs, return_logits=return_logits
                )

        # Create trainer
        trainer = ORPOTransformersTrainer(
            model=self.model,
            args=training_args,
            train_dataset=self.train_dataset,
            eval_dataset=self.eval_dataset,
            data_collator=self.data_collator,
            orpo_trainer_ref=self,
        )

        # Train
        trainer.train(resume_from_checkpoint=resume_from_checkpoint)

        return trainer

    def evaluate(
        self,
        eval_dataset: Optional[Any] = None,
    ) -> Dict[str, float]:
        """Evaluate the model."""
        from transformers import Trainer, TrainingArguments

        eval_dataset = eval_dataset or self.eval_dataset
        if eval_dataset is None:
            return {}

        training_args = TrainingArguments(
            output_dir=self.config.output_dir,
            per_device_eval_batch_size=self.config.per_device_train_batch_size,
            do_eval=True,
            report_to="none",
        )

        class ORPOTransformersTrainer(Trainer):
            def __init__(self, *args, orpo_trainer_ref=None, **kwargs):
                super().__init__(*args, **kwargs)
                self.orpo_trainer_ref = orpo_trainer_ref

            def compute_loss(self, model, inputs, return_logits=False, **kwargs):
                return self.orpo_trainer_ref.compute_loss(
                    model, inputs, return_logits=return_logits
                )

        trainer = ORPOTransformersTrainer(
            model=self.model,
            args=training_args,
            eval_dataset=eval_dataset,
            data_collator=self.data_collator,
            orpo_trainer_ref=self,
        )

        metrics = trainer.evaluate()
        return metrics

    def save_model(self, output_dir: Optional[str] = None):
        """Save the model."""
        output_dir = output_dir or self.config.output_dir
        self.model.save_pretrained(output_dir)
        self.tokenizer.save_pretrained(output_dir)


def prepare_orpo_dataset(
    dataset: List[Dict],
    tokenizer: PreTrainedTokenizerBase,
    max_seq_length: int = 512,
) -> Dict[str, Any]:
    """Prepare dataset for ORPO training.

    ORPO expects data in the format:
    [
        {
            "prompt": "User instruction...",
            "chosen": "Preferred response...",
            "rejected": "Rejected response..."
        },
        ...
    ]

    Args:
        dataset: List of preference examples
        tokenizer: Tokenizer for encoding
        max_seq_length: Maximum sequence length

    Returns:
        HuggingFace dataset with required fields
    """
    from datasets import Dataset

    def preprocess_function(examples):
        # Tokenize prompt
        prompt_encodings = tokenizer(
            examples["prompt"],
            max_length=max_seq_length,
            truncation=True,
            padding="max_length",
        )

        # Tokenize chosen response
        chosen_encodings = tokenizer(
            examples["chosen"],
            max_length=max_seq_length,
            truncation=True,
            padding="max_length",
        )

        # Tokenize rejected response
        rejected_encodings = tokenizer(
            examples["rejected"],
            max_length=max_seq_length,
            truncation=True,
            padding="max_length",
        )

        return {
            "prompt_input_ids": prompt_encodings["input_ids"],
            "prompt_attention_mask": prompt_encodings["attention_mask"],
            "chosen_input_ids": chosen_encodings["input_ids"],
            "chosen_attention_mask": chosen_encodings["attention_mask"],
            "rejected_input_ids": rejected_encodings["input_ids"],
            "rejected_attention_mask": rejected_encodings["attention_mask"],
        }

    # Convert to HF dataset
    hf_dataset = Dataset.from_list(dataset)

    # Tokenize
    processed = hf_dataset.map(
        preprocess_function,
        batched=True,
        remove_columns=hf_dataset.column_names,
    )

    return processed


# Convenience function for quick training
def train_orpo(
    model_name: str,
    train_data: List[Dict],
    config: Optional[ORPOConfig] = None,
    output_dir: str = "outputs/orpo",
    **kwargs,
) -> PreTrainedModel:
    """Quick ORPO training function.

    Args:
        model_name: HuggingFace model name
        train_data: Training data (list of prompt/chosen/rejected dicts)
        config: ORPOConfig (optional)
        output_dir: Output directory
        **kwargs: Additional arguments for ORPOConfig

    Returns:
        Trained model
    """
    from unsloth import FastLanguageModel
    import torch

    config = config or ORPOConfig(**kwargs)

    # Load model
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=model_name,
        max_seq_length=config.max_seq_length,
        dtype=torch.bfloat16 if config.bf16 else torch.float16,
        load_in_4bit=False,
    )

    # Prepare dataset
    train_dataset = prepare_orpo_dataset(train_data, tokenizer, config.max_seq_length)

    # Create trainer
    trainer = ORPOTrainer(
        model=model,
        tokenizer=tokenizer,
        config=config,
        train_dataset=train_dataset,
    )

    # Train
    trainer.train(output_dir=output_dir)

    # Save
    trainer.save_model(output_dir)

    return model
