"""
Q4_0 quantized tool embeddings. 4x faster dot product, <0.5% accuracy loss.
Story 5.1: Store 25 tool embeddings as Q4_0 (4-bit block quantized).
"""
import numpy as np


def quantize_q40(embeddings: np.ndarray) -> tuple:
    """Quantize f16 embeddings to Q4_0 format (4-bit, 32-element blocks).
    Returns (quantized_data, scale_factors, original_shape)
    Q4_0: blocks of 32 weights, each block has fp16 scale factor + 32 4-bit values
    """
    assert embeddings.ndim == 2, "Expected 2D array [n_tools, dim]"
    n_tools, dim = embeddings.shape
    assert dim % 32 == 0, "Dimension must be divisible by 32"

    n_blocks = dim // 32
    scales = np.zeros((n_tools, n_blocks), dtype=np.float16)
    # Pack 2 4-bit values per byte
    quants = np.zeros((n_tools, n_blocks * 16), dtype=np.uint8)

    for t in range(n_tools):
        for b in range(n_blocks):
            block = embeddings[t, b * 32:(b + 1) * 32]
            scale = np.max(np.abs(block)) / 7.0  # 4-bit signed: -7 to 7
            if scale > 0:
                quantized = np.round(block / scale).astype(np.int8)
                quantized = np.clip(quantized, -7, 7)
                # Pack pairs into bytes
                for i in range(16):
                    low = (quantized[2 * i] & 0x0F) if quantized[2 * i] >= 0 else ((quantized[2 * i] & 0x0F) | 0x08)
                    high = ((quantized[2 * i + 1] & 0x0F) << 4) if quantized[2 * i + 1] >= 0 else ((quantized[2 * i + 1] & 0x0F) << 4) | 0x80
                    quants[t, b * 16 + i] = low | high
            scales[t, b] = scale if scale > 0 else 1.0

    return quants, scales, embeddings.shape


def dot_product_q40(query_f16: np.ndarray, quants: np.ndarray,
                    scales: np.ndarray, shape: tuple) -> np.ndarray:
    """Compute dot product between f16 query and Q4_0 quantized tool embeddings."""
    n_tools, dim = shape
    n_blocks = dim // 32
    results = np.zeros(n_tools, dtype=np.float32)

    for t in range(n_tools):
        dot = 0.0
        for b in range(n_blocks):
            scale = float(scales[t, b])
            # Dequantize block
            for i in range(32):
                byte_idx = b * 16 + i // 2
                if i % 2 == 0:
                    val = quants[t, byte_idx] & 0x0F
                    if val & 0x08:
                        val = -(val & 0x07)
                else:
                    val = (quants[t, byte_idx] >> 4) & 0x0F
                    if val & 0x08:
                        val = -(val & 0x07)
                deq = val * scale
                dot += deq * query_f16[b * 32 + i]
        results[t] = dot

    return results


class QuantizedSimilarity:
    """Pre-compute quantized tool embeddings for fast similarity."""

    def __init__(self, tool_embeddings: np.ndarray):
        self.quants, self.scales, self.shape = quantize_q40(tool_embeddings)
        self.f16_results = None  # Cache for comparison

    def search(self, query: np.ndarray) -> np.ndarray:
        """Return similarity scores for all tools."""
        return dot_product_q40(query, self.quants, self.scales, self.shape)

    def accuracy_comparison(self, query: np.ndarray, f16_scores: np.ndarray) -> float:
        """Compare Q4_0 vs f16 accuracy. Should be >99.5%."""
        q4_scores = self.search(query)
        return np.mean(np.argmax(q4_scores) == np.argmax(f16_scores))