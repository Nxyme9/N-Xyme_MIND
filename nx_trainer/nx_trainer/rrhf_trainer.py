"""RRHF (Rank Response from Human Feedback) trainer implementation.

RRHF ranks multiple responses and optimizes the model to assign higher
probabilities to better responses. Uses a ranking loss based on human feedback.

Paper: https://arxiv.org/abs/2304.05302
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import torch
import torch.nn as nn
from torch.utils.data import Dataset


@dataclass
class RRHFConfig:
    """Configuration for RRHF trainer.

    Args:
        beta: KL divergence coefficient (default: 0.1)
        num_samples: Number of response samples to rank (default: 4)
        loss_type: Type of RRHF loss - 'rank' or 'pairwise' (default: 'rank')
        sample_strategy: How to sample responses - 'random' or 'greedy' (default: 'random')
        temperature: Sampling temperature (default: 1.0)
        use_reference: Whether to use reference model (default: True)
    """

    beta: float = field(default=0.1)
    num_samples: int = field(default=4)
    loss_type: str = field(default="rank")
    sample_strategy: str = field(default="random")
    temperature: float = field(default=1.0)
    use_reference: bool = field(default=True)


class RRHFDataset(Dataset):
    """Dataset for RRHF training.

    Each sample contains:
    - prompt: The input prompt
    - responses: List of responses with different quality levels
    - rankings: Rankings of responses (higher = better)
    """

    def __init__(self, data: List[Dict[str, Any]], tokenizer: Any, max_length: int = 2048):
        self.data = data
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self) -> int:
        return len(self.data)

    def __getitem__(self, idx: int) -> Dict[str, Any]:
        item = self.data[idx]

        # Tokenize prompt
        prompt_tokens = self.tokenizer(
            item["prompt"],
            max_length=self.max_length // 2,
            truncation=True,
            return_tensors="pt",
        )

        # Tokenize all responses
        response_tokens_list = []
        for response in item["responses"]:
            response_tokens = self.tokenizer(
                response,
                max_length=self.max_length // 2,
                truncation=True,
                return_tensors="pt",
            )
            response_tokens_list.append(
                {
                    "input_ids": response_tokens["input_ids"].squeeze(0),
                    "attention_mask": response_tokens["attention_mask"].squeeze(0),
                }
            )

        return {
            "prompt_input_ids": prompt_tokens["input_ids"].squeeze(0),
            "prompt_attention_mask": prompt_tokens["attention_mask"].squeeze(0),
            "responses": response_tokens_list,
            "rankings": item.get("rankings", list(range(len(item["responses"])))),
        }


def rrhf_loss(
    log_probs_list: List[torch.Tensor],
    rankings: List[int],
    config: RRHFConfig = None,
) -> Tuple[torch.Tensor, Dict[str, float]]:
    """Compute RRHF loss.

    Args:
        log_probs_list: List of log probabilities for each response
        rankings: Rankings for each response (higher = better)
        config: RRHF configuration

    Returns:
        Tuple of (loss, metrics dict)
    """
    config = config or RRHFConfig()

    # Stack log probabilities
    log_probs = torch.stack(log_probs_list)  # [num_samples, batch_size]

    # Convert rankings to tensor
    rankings_tensor = torch.tensor(rankings, dtype=torch.long, device=log_probs.device)

    if config.loss_type == "rank":
        # Ranking loss - maximize probability of higher-ranked responses
        # Use softmax with temperature-scaled logits
        scaled_logits = log_probs / config.temperature
        probs = nn.functional.softmax(scaled_logits, dim=0)

        # Create target distribution from rankings
        # Higher rank = higher target probability
        target_probs = nn.functional.softmax(
            torch.tensor(rankings, dtype=torch.float32, device=log_probs.device),
            dim=0,
        )

        # KL divergence between model distribution and target
        loss = nn.functional.kl_div(
            probs.log(),
            target_probs.unsqueeze(1).expand_as(probs),
            reduction="batchmean",
        )

    else:  # pairwise
        # Pairwise loss - encourage better vs worse pairs
        loss = torch.tensor(0.0, device=log_probs.device)
        count = 0

        for i in range(len(rankings)):
            for j in range(i + 1, len(rankings)):
                if rankings[i] > rankings[j]:
                    # i is better than j
                    diff = log_probs[j] - log_probs[i]
                    loss = loss + torch.clamp(diff - config.beta, min=0)
                    count += 1
                elif rankings[j] > rankings[i]:
                    # j is better than i
                    diff = log_probs[i] - log_probs[j]
                    loss = loss + torch.clamp(diff - config.beta, min=0)
                    count += 1

        if count > 0:
            loss = loss / count

    metrics = {
        "rrhf_loss": loss.item(),
        "avg_log_prob": log_probs.mean().item(),
    }

    return loss, metrics


class RRHFTrainer:
    """RRHF (Rank Response from Human Feedback) Trainer.

    Trains on ranked responses to optimize for better quality outputs.
    Works with multiple response samples per prompt.

    Usage:
        trainer = RRHFTrainer(model, tokenizer, config)
        trainer.train(train_dataset, eval_dataset)
    """

    def __init__(
        self,
        model: nn.Module,
        tokenizer: Any,
        config: RRHFConfig = None,
        optimizer: Optional[torch.optim.Optimizer] = None,
    ):
        self.model = model
        self.tokenizer = tokenizer
        self.config = config or RRHFConfig()
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

    def generate_responses(
        self,
        prompt_input_ids: torch.Tensor,
        num_responses: int = 4,
    ) -> List[Dict[str, torch.Tensor]]:
        """Generate multiple response samples for a prompt.

        Args:
            prompt_input_ids: Prompt token IDs
            num_responses: Number of responses to generate

        Returns:
            List of response token dicts
        """
        responses = []

        with torch.no_grad():
            if self.config.sample_strategy == "greedy":
                # Greedy generation
                output = self.model.generate(
                    prompt_input_ids.unsqueeze(0),
                    max_length=self.tokenizer.model_max_length // 2,
                    do_sample=False,
                )
                for _ in range(num_responses):
                    responses.append(
                        {
                            "input_ids": output.squeeze(0),
                            "attention_mask": torch.ones_like(output.squeeze(0)),
                        }
                    )

            else:  # random with temperature
                # Sampling with temperature
                output = self.model.generate(
                    prompt_input_ids.unsqueeze(0),
                    max_length=self.tokenizer.model_max_length // 2,
                    do_sample=True,
                    temperature=self.config.temperature,
                    top_k=50,
                )
                for _ in range(num_responses):
                    responses.append(
                        {
                            "input_ids": output.squeeze(0),
                            "attention_mask": torch.ones_like(output.squeeze(0)),
                        }
                    )

        return responses

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

        # Get log probabilities for each response
        log_probs_list = []
        for response in batch["responses"]:
            log_probs = self.compute_log_probs(
                response["input_ids"],
                response["attention_mask"],
            )
            log_probs_list.append(log_probs)

        # Compute RRHF loss
        loss, metrics = rrhf_loss(
            log_probs_list=log_probs_list,
            rankings=batch["rankings"],
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


# Convenience function to create RRHF trainer
def create_rrhf_trainer(
    model: nn.Module,
    tokenizer: Any,
    beta: float = 0.1,
    num_samples: int = 4,
    **kwargs,
) -> RRHFTrainer:
    """Create an RRHF trainer with given parameters.

    Args:
        model: The model to train
        tokenizer: Tokenizer
        beta: KL coefficient
        num_samples: Number of response samples
        **kwargs: Additional RRHFConfig parameters

    Returns:
        RRHFTrainer instance
    """
    config = RRHFConfig(beta=beta, num_samples=num_samples, **kwargs)
    return RRHFTrainer(model, tokenizer, config)
