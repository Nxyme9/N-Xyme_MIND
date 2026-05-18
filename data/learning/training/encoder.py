"""
RosEnna DoRA Encoder Model.
Loads Qwen2.5-0.5B with 4-bit quantization and DoRA adapters.
"""

import torch
import torch.nn as nn
from typing import List, Optional, Union
from transformers import AutoModel, AutoTokenizer, BitsAndBytesConfig
from peft import LoraConfig, get_peft_model, PeftModel, PeftConfig


class RosEnnaEncoder(nn.Module):
    """
    DoRA-based encoder for semantic routing.
    Uses Qwen2.5-0.5B with 4-bit quantization and DoRA adapters.
    Produces 896-dim normalized embeddings.
    """

    def __init__(
        self,
        base_model: str = "Qwen/Qwen2.5-0.5B",
        embedding_dim: int = 896,
        lora_r: int = 16,
        lora_alpha: int = 32,
        lora_dropout: float = 0.05,
        lora_target: Optional[List[str]] = None,
        load_in_4bit: bool = True,
        device: Optional[str] = None,
    ):
        """
        Initialize the DoRA encoder.

        Args:
            base_model: HuggingFace model ID or local path
            embedding_dim: Output embedding dimension (896 for Qwen2.5-0.5B)
            lora_r: LoRA rank
            lora_alpha: LoRA alpha scaling
            lora_dropout: LoRA dropout probability
            lora_target: List of target modules for LoRA
            load_in_4bit: Use 4-bit quantization
            device: Device to load model on (auto-detect if None)
        """
        super().__init__()

        self.base_model_name = base_model
        self.embedding_dim = embedding_dim
        self.lora_r = lora_r
        self.lora_alpha = lora_alpha
        self.lora_dropout = lora_dropout
        self.lora_target = lora_target or ["q_proj", "k_proj", "v_proj", "o_proj"]

        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        self.device = device

        # Build quantization config
        if load_in_4bit:
            self.quantization_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
            )
        else:
            self.quantization_config = None

        # Load base model and tokenizer
        self._load_base_model()

        # Setup DoRA adapters
        self._setup_dora()

        # Mean pooling layer
        self.pooler = MeanPooling()

    def _load_base_model(self) -> None:
        """Load the base Qwen model with optional quantization."""
        load_kwargs = {
            "trust_remote_code": True,
            "torch_dtype": torch.float16,
        }

        if self.quantization_config is not None:
            load_kwargs["quantization_config"] = self.quantization_config

        self.base_model = AutoModel.from_pretrained(
            self.base_model_name,
            **load_kwargs
        )
        self.base_model.to(self.device)

        self.tokenizer = AutoTokenizer.from_pretrained(
            self.base_model_name,
            trust_remote_code=True
        )

        # Ensure pad token exists
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

    def _setup_dora(self) -> None:
        """Setup DoRA adapters using PEFT."""
        lora_config = LoraConfig(
            r=self.lora_r,
            lora_alpha=self.lora_alpha,
            lora_dropout=self.lora_dropout,
            target_modules=self.lora_target,
            use_dora=True,  # Enable DoRA
            bias="none",
            task_type="FEATURE_EXTRACTION",
        )

        self.model = get_peft_model(self.base_model, lora_config)
        self.model.print_trainable_parameters()

    def train(self, mode: bool = True) -> "RosEnnaEncoder":
        """Set model to training mode."""
        super().train(mode)
        self.model.train(mode)
        return self

    def encode(self, text: str) -> torch.Tensor:
        """
        Encode a single text to embedding vector.

        Args:
            text: Input text string

        Returns:
            Normalized embedding tensor of shape (embedding_dim,)
        """
        return self.encode_batch([text])[0]

    def encode_batch(self, texts: Union[str, List[str]]) -> torch.Tensor:
        """
        Encode a batch of texts to embedding vectors.

        Args:
            texts: List of input text strings

        Returns:
            Normalized embedding tensor of shape (batch_size, embedding_dim)
        """
        if isinstance(texts, str):
            texts = [texts]

        # Tokenize
        inputs = self.tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=512,
            return_tensors="pt"
        )

        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        # Forward pass
        with torch.no_grad():
            outputs = self.model(**inputs)

        # Mean pooling over non-padding tokens
        embeddings = self.pooler(
            outputs.last_hidden_state,
            inputs["attention_mask"]
        )

        # Normalize
        embeddings = nn.functional.normalize(embeddings, p=2, dim=1)

        return embeddings

    def save_adapters(self, path: str) -> None:
        """
        Save DoRA adapters to disk.

        Args:
            path: Directory path to save adapters
        """
        self.model.save_pretrained(path)

    def load_adapters(self, path: str) -> None:
        """
        Load DoRA adapters from disk.

        Args:
            path: Directory path containing saved adapters
        """
        # Reload base model if needed
        if not hasattr(self, 'model') or self.model is None:
            self._load_base_model()

        # Load adapters
        peft_config = PeftConfig.from_pretrained(path)
        self.model = PeftModel.from_pretrained(
            self.base_model,
            path,
            config=peft_config
        )
        self.model.to(self.device)

    def get_trainable_parameters(self):
        """Return list of trainable parameters."""
        return self.model.parameters()

    def get_num_params(self):
        """Return total number of parameters."""
        return sum(p.numel() for p in self.model.parameters())

    def get_vram_usage(self) -> dict:
        """Get VRAM usage information."""
        if torch.cuda.is_available():
            return {
                "allocated": torch.cuda.memory_allocated() / 1e9,
                "reserved": torch.cuda.memory_reserved() / 1e9,
                "max_allocated": torch.cuda.max_memory_allocated() / 1e9,
            }
        return {"allocated": 0, "reserved": 0, "max_allocated": 0}


class MeanPooling(nn.Module):
    """
    Mean pooling over non-padding tokens.
    """

    def __init__(self):
        super().__init__()

    def forward(
        self,
        hidden_states: torch.Tensor,
        attention_mask: torch.Tensor
    ) -> torch.Tensor:
        """
        Apply mean pooling.

        Args:
            hidden_states: Token embeddings (batch, seq_len, hidden_dim)
            attention_mask: Attention mask (batch, seq_len)

        Returns:
            Pooled embeddings (batch, hidden_dim)
        """
        # Expand attention mask for hidden dimension
        mask = attention_mask.unsqueeze(-1).expand(hidden_states.size()).float()

        # Sum embeddings weighted by mask
        sum_embeddings = torch.sum(hidden_states * mask, dim=1)

        # Sum mask for normalization
        sum_mask = torch.clamp(mask.sum(dim=1), min=1e-9)

        # Mean pooling
        return sum_embeddings / sum_mask


class ContrastiveEncoderWrapper(nn.Module):
    """
    Wrapper for contrastive learning with dual encoders.
    Encodes queries and tool descriptions separately.
    """

    def __init__(self, encoder: RosEnnaEncoder):
        super().__init__()
        self.encoder = encoder

    def encode_query(self, texts: Union[str, List[str]]) -> torch.Tensor:
        """Encode query texts."""
        return self.encoder.encode_batch(texts)

    def encode_tool(self, texts: Union[str, List[str]]) -> torch.Tensor:
        """Encode tool description texts."""
        return self.encoder.encode_batch(texts)

    def forward(
        self,
        query_texts: List[str],
        positive_texts: List[str],
        negative_texts: Optional[List[str]] = None
    ) -> tuple:
        """
        Forward pass for contrastive learning.

        Args:
            query_texts: List of query strings
            positive_texts: List of positive tool description strings
            negative_texts: Optional list of negative tool description strings

        Returns:
            Tuple of (query_embeddings, positive_embeddings, negative_embeddings)
        """
        query_emb = self.encode_query(query_texts)
        positive_emb = self.encode_tool(positive_texts)

        negative_emb = None
        if negative_texts is not None:
            negative_emb = self.encode_tool(negative_texts)

        return query_emb, positive_emb, negative_emb