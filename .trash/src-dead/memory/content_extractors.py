"""Multi-format content extraction for memory pipeline."""

import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Binary file signature bytes for detection
BINARY_SIGNATURES = [
    b"\x89PNG",  # PNG
    b"\xff\xd8\xff",  # JPEG
    b"GIF8",  # GIF
    b"PK\x03\x04",  # ZIP/OFFICE
    b"%PDF",  # PDF
    b"\x00\x00\x01\x00",  # ICO
]


def is_binary(file_path: str) -> bool:
    """Check if file is binary by reading first 8192 bytes for null bytes.

    Args:
        file_path: Path to the file to check.

    Returns:
        True if file appears to be binary, False otherwise.
    """
    try:
        with open(file_path, "rb") as f:
            chunk = f.read(8192)
            # Check for null bytes (strong binary indicator)
            if b"\x00" in chunk:
                return True
            # Check for common binary signatures
            for sig in BINARY_SIGNATURES:
                if chunk.startswith(sig):
                    return True
            return False
    except Exception as e:
        logger.warning(f"Failed to check binary status for {file_path}: {e}")
        return True  # Default to binary on error


def get_encoding(file_path: str) -> str:
    """Detect encoding of a text file.

    Args:
        file_path: Path to the file.

    Returns:
        Detected encoding (utf-8, latin-1, or ascii).
    """
    encodings = ["utf-8", "latin-1", "ascii"]

    for encoding in encodings:
        try:
            with open(file_path, "r", encoding=encoding) as f:
                f.read(8192)
            return encoding
        except (UnicodeDecodeError, UnicodeError):
            continue

    # Fallback to utf-8 with error replacement
    return "utf-8"


def extract_code(file_path: str) -> Optional[str]:
    """Extract content from code files (text-based source files).

    Args:
        file_path: Path to the code file.

    Returns:
        File content as string, or None on failure.
    """
    try:
        if is_binary(file_path):
            logger.debug(f"Skipping binary file: {file_path}")
            return None

        encoding = get_encoding(file_path)

        with open(file_path, "r", encoding=encoding, errors="replace") as f:
            content = f.read()

        if not content or not content.strip():
            logger.warning(f"Empty file: {file_path}")
            return None

        return content

    except Exception as e:
        logger.warning(f"Failed to extract code from {file_path}: {e}")
        return None


def extract_markdown(file_path: str) -> Optional[str]:
    """Extract content from Markdown files.

    Args:
        file_path: Path to the Markdown file.

    Returns:
        File content as string, or None on failure.
    """
    try:
        if is_binary(file_path):
            logger.debug(f"Skipping binary file: {file_path}")
            return None

        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        if not content or not content.strip():
            logger.warning(f"Empty markdown file: {file_path}")
            return None

        return content

    except Exception as e:
        logger.warning(f"Failed to extract markdown from {file_path}: {e}")
        return None


def extract_text(file_path: str) -> Optional[str]:
    """Extract content from plain text files with encoding detection.

    Args:
        file_path: Path to the text file.

    Returns:
        File content as string, or None on failure.
    """
    try:
        if is_binary(file_path):
            logger.debug(f"Skipping binary file: {file_path}")
            return None

        encoding = get_encoding(file_path)

        with open(file_path, "r", encoding=encoding, errors="replace") as f:
            content = f.read()

        if not content or not content.strip():
            logger.warning(f"Empty text file: {file_path}")
            return None

        return content

    except Exception as e:
        logger.warning(f"Failed to extract text from {file_path}: {e}")
        return None


def extract_pdf(file_path: str) -> Optional[str]:
    """Extract text content from PDF files with fallback chain.

    Tries: pdfplumber -> PyPDF2 -> fitz (PyMuPDF)

    Args:
        file_path: Path to the PDF file.

    Returns:
        Extracted text content, or None on failure.
    """
    # Try pdfplumber first (best extraction quality)
    try:
        import pdfplumber

        with pdfplumber.open(file_path) as pdf:
            pages = []
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    pages.append(text)

        if pages:
            return "\n\n".join(pages)
    except ImportError:
        logger.debug("pdfplumber not available, trying next fallback")
    except Exception as e:
        logger.warning(f"pdfplumber failed for {file_path}: {e}")

    # Try PyPDF2
    try:
        import PyPDF2

        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            pages = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    pages.append(text)

        if pages:
            return "\n\n".join(pages)
    except ImportError:
        logger.debug("PyPDF2 not available, trying next fallback")
    except Exception as e:
        logger.warning(f"PyPDF2 failed for {file_path}: {e}")

    # Try fitz (PyMuPDF)
    try:
        import fitz

        doc = fitz.open(file_path)
        pages = []
        for page in doc:
            text = page.get_text()
            if text:
                pages.append(text)
        doc.close()

        if pages:
            return "\n\n".join(pages)
    except ImportError:
        logger.debug("fitz (PyMuPDF) not available")
    except Exception as e:
        logger.warning(f"fitz failed for {file_path}: {e}")

    logger.warning(f"All PDF extraction methods failed for: {file_path}")
    return None


def extract_content(file_path: str) -> Optional[str]:
    """Extract content from a file based on its extension.

    This is the main entry point that dispatches to the appropriate
    extraction function based on file type.

    Args:
        file_path: Path to the file to extract content from.

    Returns:
        Extracted content as string, or None on failure.
    """
    if not os.path.exists(file_path):
        logger.warning(f"File does not exist: {file_path}")
        return None

    ext = Path(file_path).suffix.lower()

    # PDF
    if ext == ".pdf":
        return extract_pdf(file_path)

    # Markdown variants
    if ext in {".md", ".markdown", ".mdown", ".mkd"}:
        return extract_markdown(file_path)

    # Code files (text-based)
    code_extensions = {
        ".py",
        ".js",
        ".ts",
        ".tsx",
        ".jsx",
        ".java",
        ".c",
        ".cpp",
        ".h",
        ".hpp",
        ".go",
        ".rs",
        ".rb",
        ".php",
        ".swift",
        ".kt",
        ".scala",
        ".cs",
        ".vb",
        ".html",
        ".css",
        ".scss",
        ".sass",
        ".less",
        ".json",
        ".yaml",
        ".yml",
        ".toml",
        ".xml",
        ".sql",
        ".sh",
        ".bash",
        ".zsh",
        ".ps1",
        ".bat",
        ".cmd",
        ".r",
        ".lua",
        ".pl",
        ".pm",
        ".ex",
        ".exs",
        ".erl",
        ".hs",
        ".ml",
        ".vue",
        ".svelte",
        ".dart",
        ".groovy",
        ".gradle",
        ".ini",
        ".cfg",
        ".txt",
        ".text",
        ".log",
        ".env",
        ".gitignore",
        ".dockerignore",
    }

    if ext in code_extensions:
        return extract_code(file_path)

    # Fallback to text extraction for unknown extensions
    return extract_text(file_path)
