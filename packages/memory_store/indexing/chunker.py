"""Chunker — Text chunking for memory indexing.

Combines:
- chunker.py: Token-based text chunking
- metadata_extractor.py: Metadata extraction
- content_extractor.py, content_extractors.py: Content extraction (merged into one)
"""

import logging
import os
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

DEFAULT_CHUNK_SIZE = 512
DEFAULT_CHUNK_OVERLAP = 50


def count_tokens(text: str) -> int:
    """Approximate token count."""
    if not text:
        return 0
    words = text.split()
    return int(len(words) * 0.75)


def chunk_by_tokens(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> List[str]:
    """Split text into chunks based on token count with overlap."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if chunk_overlap < 0:
        raise ValueError("chunk_overlap must be non-negative")
    if not text:
        return []

    words = text.split()
    if not words:
        return []
    if count_tokens(text) <= chunk_size:
        return [text]

    chunks = []
    current_pos = 0
    text_len = len(words)
    tokens_per_word = 0.75

    while current_pos < text_len:
        max_words = int(chunk_size / tokens_per_word)
        end_pos = min(current_pos + max_words, text_len)
        chunk = " ".join(words[current_pos:end_pos])
        chunks.append(chunk)
        overlap_words = int(chunk_overlap / tokens_per_word)
        next_pos = current_pos + max_words - overlap_words
        if next_pos <= current_pos:
            next_pos = current_pos + max_words
        current_pos = next_pos
        if current_pos >= text_len:
            break

    return chunks


def chunk_by_lines(text: str, max_lines: int = 100) -> List[str]:
    """Split text into chunks based on line count."""
    lines = text.split("\n")
    if len(lines) <= max_lines:
        return [text]
    chunks = []
    for i in range(0, len(lines), max_lines):
        chunks.append("\n".join(lines[i : i + max_lines]))
    return chunks


def extract_code(file_path: str) -> str:
    """Extract content from code files."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except Exception as e:
        logger.debug(f"Failed to read code file {file_path}: {e}")
        return ""


def extract_pdf(file_path: str) -> str:
    """Extract text from PDF files."""
    try:
        import fitz

        doc = fitz.open(file_path)
        text = ""
        for page in doc:
            text += page.get_text()
            if len(text) > 50000:
                break
        doc.close()
        return text[:50000]
    except ImportError:
        logger.debug(f"PyMuPDF not installed, cannot extract PDF: {file_path}")
    except Exception as e:
        logger.debug(f"PDF extraction failed for {file_path}: {e}")
    return ""


def extract_docx(file_path: str) -> str:
    """Extract text from DOCX files."""
    try:
        from docx import Document

        doc = Document(file_path)
        text = "\n".join([p.text for p in doc.paragraphs if p.text])
        return text
    except ImportError:
        logger.debug(f"python-docx not installed, cannot extract DOCX: {file_path}")
    except Exception as e:
        logger.debug(f"DOCX extraction failed for {file_path}: {e}")
    return ""


def extract_content(
    file_path: str, file_type: str = "code", max_chars: int = 50000
) -> str:
    """Extract text content from a file."""
    if not os.path.exists(file_path):
        return ""

    ext = Path(file_path).suffix.lower()
    if ext == ".pdf":
        return extract_pdf(file_path)[:max_chars]
    if ext == ".docx":
        return extract_docx(file_path)[:max_chars]
    return extract_code(file_path)[:max_chars]


def extract_metadata(file_path: str) -> dict:
    """Extract basic metadata from a file."""
    try:
        stat = os.stat(file_path)
        return {
            "size": stat.st_size,
            "mtime": stat.st_mtime,
            "name": Path(file_path).name,
            "ext": Path(file_path).suffix,
        }
    except OSError as e:
        logger.debug(f"Failed to get metadata for {file_path}: {e}")
        return {}


class Chunker:
    """Text chunker with token-based splitting."""

    def __init__(
        self,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk(self, text: str) -> List[str]:
        return chunk_by_tokens(text, self.chunk_size, self.chunk_overlap)


class MetadataChunker:
    """Chunker with metadata extraction."""

    def __init__(self, chunker: Optional[Chunker] = None):
        self.chunker = chunker or Chunker()

    def chunk_with_metadata(self, text: str, source: str) -> List[dict]:
        chunks = self.chunker.chunk(text)
        return [
            {"content": chunk, "source": source, "index": i}
            for i, chunk in enumerate(chunks)
        ]


__all__ = [
    "Chunker",
    "MetadataChunker",
    "chunk_by_tokens",
    "chunk_by_lines",
    "extract_content",
    "extract_metadata",
]
