"""BCO (Batch Conditional Optimization) trainer implementation.

BCO optimizes LLMs using conditional generation with batch-level optimization.
Uses batch-wise comparison to improve multiple responses simultaneously.

Paper: https://arxiv.org/abs/2402.11759
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import torch
import torch.nn as nn
from torch.utils.data import Dataset


@dataclass
class BCOConfig:
    """Configuration for BCO trainer.

    Args:
        beta: KL divergence coefficient (default: 0.1)
        delta: Confidence threshold for BCO (default: 0.5)
        use_dynamic_threshold: Whether to use dynamic threshold (default: True)
        batch_compare: Compare within batch (default: True)
        loss_type: Type of BCO loss (default: 'contrastive')
        margin: Margin for contrastive loss (default: 0.3)
    """

    beta: float = field(default=0.1)
    delta: float = field(default=0.5)
    use_dynamic_threshold: bool = field(default=True)
    batch_compare: bool = field(default=True)
    loss_type: str = field(default="contrastive")
    margin: float = field(default=0.3)


class BCOBatchCollator:
    """Collator for BCO batches with conditional generation."""

    def __init__(self, tokenizer: Any, max_length: int = 2048):
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __call__(self, batch: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Collate batch with conditional generation data.

        Args:
            batch: List of samples

        Returns:
            Collated batch
        """
        prompt_input_ids = []
        prompt_attention_mask = []
        chosen_response_ids = []
        chosen_response_mask = []
        rejected_response_ids = []
        rejected_response_mask = []
        conditions = []

        for item in batch:
            prompt_input_ids.append(item["prompt_input_ids"])
            prompt_attention_mask.append(item["prompt_attention_mask"])
            chosen_response_ids.append(item["chosen_input_ids"])
            chosen_response_mask.append(item["chosen_attention_mask"])
            rejected_response_ids.append(item["rejected_input_ids"])
            rejected_response_mask.append(item["rejected_attention_mask"])
            conditions.append(item.get("condition", "default"))

        return {
            "prompt_input_ids": torch.stack(prompt_input_ids),
            "prompt_attention_mask": torch.stack(prompt_attention_mask),
            "chosen_input_ids": torch.stack(chosen_response_ids),
            "chosen_attention_mask": torch.stack(chosen_response_mask),
            "rejected_input_ids": torch.stack(rejected_response_ids),
            "rejected_attention_mask": torch.stack(rejected_response_mask),
            "conditions": conditions,
        }


def bco_loss(
    policy_chosen_logps: torch.Tensor,
    policy_rejected_logps: torch.Tensor,
    reference_chosen_logps: Optional[torch.Tensor] = None,
    reference_rejected_logps: Optional[torch.Tensor] = None,
    conditions: Optional[List[str]] = None,
    config: BCOConfig = None,
) -> Tuple[torch.Tensor, Dict[str, float]]:
    """Compute BCO loss.

    Args:
        policy_chosen_logps: Log probabilities for chosen responses
        policy_rejected_logps: Log probabilities for rejected responses
        reference_chosen_logps: Reference log probs for chosen
        reference_rejected_logps: Reference log probs for rejected
        conditions: Condition strings for each sample
        config: BCO configuration

    Returns:
        Tuple of (loss, metrics dict)
    """
    config = config or BCOConfig()

    # Compute log ratio differences
    if config.use_dynamic_threshold:
        # Dynamic threshold based on batch statistics
        batch_mean = (policy_chosen_logps - policy_rejected_logps).mean()
        threshold = torch.sigmoid(batch_mean) * config.delta
    else:
        threshold = config.delta

    # BCO contrastive loss
    if config.loss_type == "contrastive":
        # Contrastive loss - push apart chosen and rejected
        diff = policy_chosen_logps - policy_rejected_logps

        # Soft margin loss
        loss = torch.clamp(config.margin - diff, min=0).mean()

        # Add KL penalty
        if reference_chosen_logps is not None and reference_rejected_logps is not None:
            kl_chosen = nn.functional.kl_div(
                policy_chosen_logps.log(), reference_chosen_logps, reduction="batchmean"
            )
            kl_rejected = nn.functional.kl_div(
                policy_rejected_logps.log(), reference_rejected_logps, reduction="batchmean"
            )
            loss = loss + config.beta * (kl_chosen + kl_rejected)

    else:  # ranking loss
        # Ranking loss - similar to DPO but batch-aware
        logits = torch.stack([policy_chosen_logps, policy_rejected_logps], dim=0)
        loss = nn.functional.cross_entropy(
            logits.unsqueeze(0),
            torch.zeros(1, dtype=torch.long, device=logits.device),
        )

        # Add KL penalty if reference available
        if reference_chosen_logps is not None:
            kl = config.beta * (policy_chosen_logps - reference_chosen_logps).mean()
            loss = loss + kl

    # Compute metrics
    chosen_acc = (policy_chosen_logps > policy_rejected_logps + threshold).float().mean()
    metrics = {
        "bco_loss": loss.item(),
        "chosen_accuracy": chosen_acc.item(),
        "avg_chosen_logp": policy_chosen_logps.mean().item(),
        "avg_rejected_logp": policy_rejected_logps.mean().item(),
    }

    return loss, metrics


class BCOTrainer:
    """BCO (Batch Conditional Optimization) Trainer.

    Trains on preference pairs with batch-level conditional optimization.
    Uses dynamic thresholding based on batch statistics.

    Usage:
        trainer = BCOTrainer(model, tokenizer, config)
        trainer.train(train_dataset, eval_dataset)
    """

    def __init__(
        self,
        model: nn.Module,
        tokenizer: Any,
        config: BCOConfig = None,
        optimizer: Optional[torch.optim.Optimizer] = None,
    ):
        self.model = model
        self.tokenizer = tokenizer
        self.config = config or BCOConfig()
        self.optimizer = optimizer or torch.optim.AdamW(model.parameters(), lr=1e-5)

    def compute_log_probs(
        self,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor,
    ) -> torch.Tensor:
        """Compute log probabilities for given inputs."""
        with torch.no_grad():
            outputs = self.model(input_ids=input_ids, attention_mask=attention_mask)
            logits = outputs.logits
            log_probs = nn.functional.log_softmax(logits, dim=-1)
            return log_probs.mean(dim=-1)

    def train_step(
        self,
        batch: Dict[str, Any],
    ) -> Dict[str, float]:
        """Single training step.

        Args:
            batch: Batch containing prompt and response tokens

        Returns:
            Metrics dict
        """
        self.model.train()

        # Get log probabilities for chosen and rejected
        chosen_logps = self.compute_log_probs(
            batch["chosen_input_ids"],
            batch["chosen_attention_mask"],
        )
        rejected_logps = self.compute_log_probs(
            batch["rejected_input_ids"],
            batch["rejected_attention_mask"],
        )

        # Compute BCO loss
        loss, metrics = bco_loss(
            policy_chosen_logps=chosen_logps,
            policy_rejected_logps=rejected_logps,
            conditions=batch.get("conditions"),
            config=self.config,
        )

        # Backward pass
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()

        return metrics

    def train(
        self,
        train_dataset: Dataset,
        eval_dataset: Optional[Dataset] = None,
        num_epochs: int = 3,
        batch_size: int = 4,
    ):
        """Train the model.

        Args:
            train_dataset: Training dataset
            eval_dataset: Optional evaluation dataset
            num_epochs: Number of training epochs
            batch_size: Batch size
        """
        from torch.utils.data import DataLoader
        from functools import partial

        collator_fn = BCOBatchCollator(self.tokenizer)
        train_loader = DataLoader(
            train_dataset,
            batch_size=batch_size,
            shuffle=True,
            collate_fn=collator_fn,
        )

        for epoch in range(num_epochs):
            for batch in train_loader:
                metrics = self.train_step(batch)
                print(f"Epoch {epoch + 1}: {metrics}")

        print("Training complete!")


# Convenience function to create BCO trainer
def create_bco_trainer(
    model: nn.Module,
    tokenizer: Any,
    beta: float = 0.1,
    delta: float = 0.5,
    **kwargs,
) -> BCOTrainer:
    """Create a BCO trainer with given parameters.

    Args:
        model: The model to train
        tokenizer: Tokenizer
        beta: KL coefficient
        delta: Confidence threshold
        **kwargs: Additional BCOConfig parameters

    Returns:
        BCOTrainer instance
    """
    config = BCOConfig(beta=beta, delta=delta, **kwargs)
    return BCOTrainer(model, tokenizer, config)
