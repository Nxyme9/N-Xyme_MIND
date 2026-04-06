"""Token-based text chunking for memory pipeline."""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Default chunking parameters
DEFAULT_CHUNK_SIZE = 512
DEFAULT_CHUNK_OVERLAP = 50


def count_tokens(text: str) -> int:
    """Approximate token count using whitespace split.

    Args:
        text: Input text to count tokens for.

    Returns:
        Approximate token count (word count * 0.75 for typical tokenization).
    """
    if not text:
        return 0
    # Split by whitespace and count words
    words = text.split()
    # Approximate: 1 token ≈ 0.75 words for typical tokenization
    return int(len(words) * 0.75)


def chunk_by_tokens(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    """Split text into chunks based on token count with overlap.

    Args:
        text: Input text to chunk.
        chunk_size: Maximum tokens per chunk.
        chunk_overlap: Number of tokens to overlap between chunks.

    Returns:
        List of text chunks.

    Raises:
        ValueError: If chunk_size <= 0 or chunk_overlap < 0.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if chunk_overlap < 0:
        raise ValueError("chunk_overlap must be non-negative")

    if not text:
        return []

    # Split into words
    words = text.split()
    if not words:
        return []

    # If text is shorter than chunk size, return as single chunk
    if count_tokens(text) <= chunk_size:
        return [text]

    chunks = []
    current_pos = 0
    text_len = len(words)

    # Calculate approximate tokens per word for conversion
    tokens_per_word = 0.75

    while current_pos < text_len:
        # Calculate end position based on token limit
        # chunk_size words ≈ chunk_size / 0.75 tokens
        max_words = int(chunk_size / tokens_per_word)
        end_pos = min(current_pos + max_words, text_len)

        # Extract chunk
        chunk = " ".join(words[current_pos:end_pos])
        chunks.append(chunk)

        # Move position with overlap
        # Overlap in words = chunk_overlap / 0.75
        overlap_words = int(chunk_overlap / tokens_per_word)
        next_pos = current_pos + max_words - overlap_words

        # Avoid infinite loop if overlap is too large
        if next_pos <= current_pos:
            next_pos = current_pos + max_words

        current_pos = next_pos

        # Stop if we've reached the end
        if current_pos >= text_len:
            break

    return chunks


def chunk_by_lines(text: str, max_lines: int = 100) -> list[str]:
    """Split text into chunks based on line count (fallback for code).

    Args:
        text: Input text to chunk.
        max_lines: Maximum lines per chunk.

    Returns:
        List of text chunks (each with at most max_lines).
    """
    if not text:
        return []

    if max_lines <= 0:
        raise ValueError("max_lines must be positive")

    lines = text.split("\n")
    if not lines:
        return []

    # If text has fewer lines than max_lines, return as single chunk
    if len(lines) <= max_lines:
        return [text]

    chunks = []
    for i in range(0, len(lines), max_lines):
        chunk = "\n".join(lines[i : i + max_lines])
        chunks.append(chunk)

    return chunks


def chunk_text(
    text: str,
    file_path: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[dict]:
    """Main chunking function with metadata.

    Args:
        text: Input text to chunk.
        file_path: Path to the source file (for metadata).
        chunk_size: Maximum tokens per chunk (default: 512).
        chunk_overlap: Number of tokens to overlap (default: 50).

    Returns:
        List of chunk dictionaries with metadata:
        - text: The chunk text
        - chunk_index: Index of this chunk (0-based)
        - total_chunks: Total number of chunks
        - file_path: Source file path
        - start_char: Character position where chunk starts
        - end_char: Character position where chunk ends
        - token_count: Number of tokens in this chunk
    """
    # Handle empty text
    if not text or not text.strip():
        logger.debug(f"Empty text provided for {file_path}")
        return []

    # Handle text shorter than chunk_size
    if count_tokens(text) <= chunk_size:
        return [
            {
                "text": text,
                "chunk_index": 0,
                "total_chunks": 1,
                "file_path": file_path,
                "start_char": 0,
                "end_char": len(text),
                "token_count": count_tokens(text),
            }
        ]

    # Use token-based chunking for non-code files (prose, markdown, etc.)
    # Use line-based chunking for code files
    extension = file_path.split(".")[-1].lower() if "." in file_path else ""
    code_extensions = {
        "py",
        "js",
        "ts",
        "tsx",
        "jsx",
        "java",
        "c",
        "cpp",
        "h",
        "hpp",
        "go",
        "rs",
        "rb",
        "php",
        "swift",
        "kt",
        "scala",
        "cs",
        "vb",
        "html",
        "css",
        "scss",
        "sass",
        "less",
        "json",
        "yaml",
        "yml",
        "toml",
        "xml",
        "sql",
        "sh",
        "bash",
        "zsh",
        "ps1",
        "bat",
        "cmd",
        "r",
        "lua",
        "pl",
        "pm",
        "ex",
        "exs",
        "erl",
        "hs",
        "ml",
        "vue",
        "svelte",
        "dart",
        "groovy",
        "gradle",
    }

    # Choose chunking strategy based on file type
    if extension in code_extensions:
        raw_chunks = chunk_by_lines(text, max_lines=50)
    else:
        raw_chunks = chunk_by_tokens(text, chunk_size, chunk_overlap)

    # If we got only 1 chunk but text has more tokens than chunk_size,
    # try line-based as fallback (handles edge case of single very long line)
    if len(raw_chunks) == 1 and count_tokens(text) > chunk_size:
        # Try line-based with more aggressive splitting
        line_chunks = chunk_by_lines(text, max_lines=30)
        if len(line_chunks) > 1:
            raw_chunks = line_chunks

    # Build chunk metadata
    chunks = []
    total_chunks = len(raw_chunks)

    for idx, chunk_text_val in enumerate(raw_chunks):
        # Calculate character positions
        # This is approximate since we use pre-chunked text
        if idx == 0:
            start_char = 0
        else:
            # Find approximate start based on previous chunks
            start_char = sum(len(c) + 1 for c in raw_chunks[:idx])

        end_char = start_char + len(chunk_text_val)

        chunks.append(
            {
                "text": chunk_text_val,
                "chunk_index": idx,
                "total_chunks": total_chunks,
                "file_path": file_path,
                "start_char": start_char,
                "end_char": end_char,
                "token_count": count_tokens(chunk_text_val),
            }
        )

    return chunks
