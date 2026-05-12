"""PRO (Preference Regularized Optimization) trainer implementation.

PRO optimizes LLMs using preference data without requiring reference models.
It uses a ranking-based loss that encourages preferred responses over rejected ones.

Paper: https://arxiv.org/abs/2406.05882
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import torch
import torch.nn as nn
from torch.utils.data import Dataset


@dataclass
class PROConfig:
    """Configuration for PRO trainer.

    Args:
        beta: KL divergence coefficient (default: 0.1)
        lambda_: Margin for ranking loss (default: 0.5)
        margin_type: Type of margin - 'linear' or 'log' (default: 'linear')
        reference_free: Whether to train without reference model (default: True)
        loss_type: Type of ranking loss - 'margin' or 'softmax' (default: 'margin')
    """

    beta: float = field(default=0.1)
    lambda_: float = field(default=0.5)
    margin_type: str = field(default="linear")
    reference_free: bool = field(default=True)
    loss_type: str = field(default="margin")


class PRODataset(Dataset):
    """Dataset for PRO training.

    Each sample contains:
    - prompt: The input prompt
    - chosen: The preferred response
    - rejected: The rejected response
    """

    def __init__(self, data: List[Dict[str, str]], tokenizer: Any, max_length: int = 2048):
        self.data = data
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self) -> int:
        return len(self.data)

    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        item = self.data[idx]

        # Tokenize prompt
        prompt_tokens = self.tokenizer(
            item["prompt"],
            max_length=self.max_length // 2,
            truncation=True,
            return_tensors="pt",
        )

        # Tokenize chosen response
        chosen_tokens = self.tokenizer(
            item["chosen"],
            max_length=self.max_length // 2,
            truncation=True,
            return_tensors="pt",
        )

        # Tokenize rejected response
        rejected_tokens = self.tokenizer(
            item["rejected"],
            max_length=self.max_length // 2,
            truncation=True,
            return_tensors="pt",
        )

        return {
            "prompt_input_ids": prompt_tokens["input_ids"].squeeze(0),
            "prompt_attention_mask": prompt_tokens["attention_mask"].squeeze(0),
            "chosen_input_ids": chosen_tokens["input_ids"].squeeze(0),
            "chosen_attention_mask": chosen_tokens["attention_mask"].squeeze(0),
            "rejected_input_ids": rejected_tokens["input_ids"].squeeze(0),
            "rejected_attention_mask": rejected_tokens["attention_mask"].squeeze(0),
        }


def pro_loss(
    policy_chosen_logps: torch.Tensor,
    policy_rejected_logps: torch.Tensor,
    reference_chosen_logps: Optional[torch.Tensor] = None,
    reference_rejected_logps: Optional[torch.Tensor] = None,
    config: PROConfig = None,
) -> Tuple[torch.Tensor, Dict[str, float]]:
    """Compute PRO loss.

    Args:
        policy_chosen_logps: Log probabilities for chosen responses
        policy_rejected_logps: Log probabilities for rejected responses
        reference_chosen_logps: Reference log probs for chosen (if not reference_free)
        reference_rejected_logps: Reference log probs for rejected (if not reference_free)
        config: PRO configuration

    Returns:
        Tuple of (loss, metrics dict)
    """
    config = config or PROConfig()

    # Compute log ratio differences
    if config.reference_free:
        # Reference-free PRO loss
        chosen_loss = -policy_chosen_logps
        rejected_loss = policy_rejected_logps
    else:
        # PRO with reference model (KL regularized)
        if reference_chosen_logps is None or reference_rejected_logps is None:
            raise ValueError("Reference logps required when reference_free=False")

        chosen_loss = -(policy_chosen_logps - reference_chosen_logps).mean() * config.beta
        rejected_loss = (policy_rejected_logps - reference_rejected_logps).mean() * config.beta

    # Compute ranking loss with margin
    if config.loss_type == "margin":
        # Margin-based ranking loss
        if config.margin_type == "linear":
            margin = config.lambda_
        else:  # log margin
            margin = torch.log(torch.tensor(config.lambda_))

        # Loss = max(0, margin - (chosen_logprob - rejected_logprob))
        diff = policy_chosen_logps - policy_rejected_logps
        loss = torch.clamp(margin - diff, min=0).mean()

    else:  # softmax
        # Softmax-based ranking loss
        logits = torch.stack([policy_chosen_logps, policy_rejected_logps], dim=0)
        loss = nn.functional.cross_entropy(
            logits.unsqueeze(0), torch.zeros(1, dtype=torch.long, device=logits.device)
        )

    # Total loss
    total_loss = chosen_loss.mean() + rejected_loss.mean() + loss

    metrics = {
        "chosen_loss": chosen_loss.mean().item(),
        "rejected_loss": rejected_loss.mean().item(),
        "ranking_loss": loss.item(),
        "total_loss": total_loss.item(),
    }

    return total_loss, metrics


class PROTrainer:
    """PRO (Preference Regularized Optimization) Trainer.

    Trains on preference pairs (chosen/rejected) to optimize for preferred outputs.

    Usage:
        trainer = PROTrainer(model, tokenizer, config)
        trainer.train(train_dataset, eval_dataset)
    """

    def __init__(
        self,
        model: nn.Module,
        tokenizer: Any,
        config: PROConfig = None,
        optimizer: Optional[torch.optim.Optimizer] = None,
    ):
        self.model = model
        self.tokenizer = tokenizer
        self.config = config or PROConfig()
        self.optimizer = optimizer or torch.optim.AdamW(model.parameters(), lr=1e-5)

    def compute_log_probs(
        self,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor,
    ) -> torch.Tensor:
        """Compute log probabilities for given inputs."""
        with torch.no_grad():
            outputs = self.model(input_ids=input_ids, attention_mask=attention_mask)
            # Get logits and compute log probs
            logits = outputs.logits
            log_probs = nn.functional.log_softmax(logits, dim=-1)

            # Get log prob of each token
            # For simplicity, return mean log prob per sequence
            return log_probs.mean(dim=-1)

    def train_step(
        self,
        batch: Dict[str, torch.Tensor],
    ) -> Dict[str, float]:
        """Single training step.

        Args:
            batch: Batch containing prompt, chosen, rejected tokens

        Returns:
            Metrics dict
        """
        self.model.train()

        # Get log probabilities
        chosen_logps = self.compute_log_probs(
            batch["chosen_input_ids"],
            batch["chosen_attention_mask"],
        )
        rejected_logps = self.compute_log_probs(
            batch["rejected_input_ids"],
            batch["rejected_attention_mask"],
        )

        # Compute loss
        loss, metrics = pro_loss(
            policy_chosen_logps=chosen_logps,
            policy_rejected_logps=rejected_logps,
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

        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)

        for epoch in range(num_epochs):
            for batch in train_loader:
                metrics = self.train_step(batch)
                print(f"Epoch {epoch + 1}: {metrics}")

        print("Training complete!")


# Convenience function to create PRO trainer
def create_pro_trainer(
    model: nn.Module,
    tokenizer: Any,
    beta: float = 0.1,
    lambda_: float = 0.5,
    **kwargs,
) -> PROTrainer:
    """Create a PRO trainer with given parameters.

    Args:
        model: The model to train
        tokenizer: Tokenizer
        beta: KL coefficient
        lambda_: Margin
        **kwargs: Additional PROConfig parameters

    Returns:
        PROTrainer instance
    """
    config = PROConfig(beta=beta, lambda_=lambda_, **kwargs)
    return PROTrainer(model, tokenizer, config)
