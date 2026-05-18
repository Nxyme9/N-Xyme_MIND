"""
Contrastive Loss Functions for RosEnna Trainer.
Implements InfoNCE (Multi-Negatives Ranking) and GIST embedding losses.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Optional


def compute_similarity_matrix(embeddings: torch.Tensor) -> torch.Tensor:
    """
    Compute cosine similarity matrix for a batch of embeddings.

    Args:
        embeddings: Embedding tensor of shape (batch_size, embedding_dim)

    Returns:
        Similarity matrix of shape (batch_size, batch_size)
    """
    # Normalize embeddings
    normalized = F.normalize(embeddings, p=2, dim=1)

    # Cosine similarity = dot product of normalized vectors
    sim_matrix = torch.mm(normalized, normalized.T)

    return sim_matrix


def multi_negatives_ranking_loss(
    anchor_emb: torch.Tensor,
    positive_emb: torch.Tensor,
    temperature: float = 0.05
) -> torch.Tensor:
    """
    Multi-Negatives Ranking (InfoNCE) Loss.
    Computes contrastive loss where each anchor is compared against
    multiple positives (in-batch negatives).

    Args:
        anchor_emb: Anchor embeddings (batch_size, embedding_dim)
        positive_emb: Positive embeddings (batch_size, embedding_dim)
        temperature: Temperature scaling factor for logits

    Returns:
        Scalar loss value
    """
    batch_size = anchor_emb.size(0)

    if batch_size == 1:
        # Need at least 2 samples for contrastive loss
        return torch.tensor(0.0, device=anchor_emb.device)

    # Compute cosine similarities
    # For InfoNCE: each anchor should match its corresponding positive
    # We use symmetric loss: anchor->positive AND positive->anchor

    # Normalize embeddings
    anchor_norm = F.normalize(anchor_emb, p=2, dim=1)
    positive_norm = F.normalize(positive_emb, p=2, dim=1)

    # Compute similarity matrix: (batch_size, batch_size)
    # sim[i,j] = similarity between anchor_i and positive_j
    logits = torch.mm(anchor_norm, positive_norm.T) / temperature

    # Labels are diagonal: anchor_i matches positive_i
    labels = torch.arange(batch_size, device=anchor_emb.device)

    # Symmetric loss: anchor->positive and positive->anchor
    loss_anchor_to_pos = F.cross_entropy(logits, labels)

    # Also compute positive to anchor
    logits_pos = torch.mm(positive_norm, anchor_norm.T) / temperature
    loss_pos_to_anchor = F.cross_entropy(logits_pos, labels)

    # Combined loss
    loss = (loss_anchor_to_pos + loss_pos_to_anchor) / 2

    return loss


def gist_embed_loss(
    anchor_emb: torch.Tensor,
    positive_emb: torch.Tensor,
    negative_emb: Optional[torch.Tensor] = None,
    temperature: float = 0.05
) -> torch.Tensor:
    """
    GIST Embedding Loss with hard negatives support.
    Computes contrastive loss using both in-batch negatives and explicit negatives.

    Args:
        anchor_emb: Anchor embeddings (batch_size, embedding_dim)
        positive_emb: Positive embeddings (batch_size, embedding_dim)
        negative_emb: Optional hard negative embeddings (batch_size, num_negatives, embedding_dim)
        temperature: Temperature scaling factor

    Returns:
        Scalar loss value
    """
    batch_size = anchor_emb.size(0)

    if batch_size == 1:
        return torch.tensor(0.0, device=anchor_emb.device)

    # Normalize embeddings
    anchor_norm = F.normalize(anchor_emb, p=2, dim=1)
    positive_norm = F.normalize(positive_emb, p=2, dim=1)

    # In-batch similarity matrix
    in_batch_logits = torch.mm(anchor_norm, positive_norm.T) / temperature

    # Add hard negatives if provided
    if negative_emb is not None:
        # negative_emb: (batch_size, num_negatives, embedding_dim)
        num_negatives = negative_emb.size(1)
        neg_flat = negative_emb.view(-1, negative_emb.size(-1))  # (batch*neg, dim)
        neg_norm = F.normalize(neg_flat, p=2, dim=1)

        # Compute similarity to hard negatives
        hard_neg_logits = torch.mm(anchor_norm, neg_norm.T) / temperature  # (batch, batch*neg)

        # Reshape to (batch, batch, num_negatives) and take max per negative sample
        hard_neg_logits = hard_neg_logits.view(batch_size, batch_size, num_negatives)

        # For each anchor, take the max similarity to any negative from each positive sample
        hard_neg_max, _ = hard_neg_logits.max(dim=2)  # (batch, batch)

        # Concatenate in-batch and hard negatives
        logits = torch.cat([in_batch_logits, hard_neg_max], dim=1)
    else:
        logits = in_batch_logits

    # Labels are diagonal (anchor_i matches positive_i)
    labels = torch.arange(batch_size, device=anchor_emb.device)

    loss = F.cross_entropy(logits, labels)

    return loss


def triplet_loss(
    anchor_emb: torch.Tensor,
    positive_emb: torch.Tensor,
    negative_emb: torch.Tensor,
    margin: float = 0.5
) -> torch.Tensor:
    """
    Triplet loss with margin.
    Ensures positive is closer than negative by at least margin.

    Args:
        anchor_emb: Anchor embeddings (batch_size, embedding_dim)
        positive_emb: Positive embeddings (batch_size, embedding_dim)
        negative_emb: Negative embeddings (batch_size, embedding_dim)
        margin: Minimum distance margin between positive and negative

    Returns:
        Scalar loss value
    """
    # Normalize embeddings
    anchor_norm = F.normalize(anchor_emb, p=2, dim=1)
    positive_norm = F.normalize(positive_emb, p=2, dim=1)
    negative_norm = F.normalize(negative_emb, p=2, dim=1)

    # Compute distances
    pos_dist = 1 - F.cosine_similarity(anchor_norm, positive_norm, dim=1)
    neg_dist = 1 - F.cosine_similarity(anchor_norm, negative_norm, dim=1)

    # Triplet loss
    losses = F.relu(pos_dist - neg_dist + margin)

    return losses.mean()


def accuracy_at_k(
    anchor_emb: torch.Tensor,
    positive_emb: torch.Tensor,
    k: int = 1
) -> float:
    """
    Compute top-k accuracy of positive matching.

    Args:
        anchor_emb: Anchor embeddings (batch_size, embedding_dim)
        positive_emb: Positive embeddings (batch_size, embedding_dim)
        k: Number of top predictions to consider

    Returns:
        Accuracy as float between 0 and 1
    """
    batch_size = anchor_emb.size(0)

    # Compute similarity matrix
    sim_matrix = compute_similarity_matrix(anchor_emb)

    # Get top-k indices for each anchor
    _, top_k_indices = torch.topk(sim_matrix, k=k, dim=1)

    # Check if positive index is in top-k
    positive_indices = torch.arange(batch_size, device=anchor_emb.device)

    correct = 0
    for i in range(batch_size):
        if positive_indices[i] in top_k_indices[i]:
            correct += 1

    return correct / batch_size


class ContrastiveLoss(nn.Module):
    """
    Combined contrastive loss module.
    """

    def __init__(
        self,
        loss_type: str = "mnr",
        temperature: float = 0.05,
        use_hard_negatives: bool = False
    ):
        """
        Initialize contrastive loss.

        Args:
            loss_type: "mnr" for Multi-Negatives Ranking, "gist" for GIST loss
            temperature: Temperature scaling
            use_hard_negatives: Whether to use explicit hard negatives
        """
        super().__init__()
        self.loss_type = loss_type
        self.temperature = temperature
        self.use_hard_negatives = use_hard_negatives

    def forward(
        self,
        anchor_emb: torch.Tensor,
        positive_emb: torch.Tensor,
        negative_emb: Optional[torch.Tensor] = None
    ) -> torch.Tensor:
        """
        Compute contrastive loss.

        Args:
            anchor_emb: Anchor embeddings
            positive_emb: Positive embeddings
            negative_emb: Optional hard negatives

        Returns:
            Loss tensor
        """
        if self.loss_type == "mnr":
            return multi_negatives_ranking_loss(
                anchor_emb,
                positive_emb,
                self.temperature
            )
        elif self.loss_type == "gist":
            return gist_embed_loss(
                anchor_emb,
                positive_emb,
                negative_emb if self.use_hard_negatives else None,
                self.temperature
            )
        else:
            raise ValueError(f"Unknown loss type: {self.loss_type}")