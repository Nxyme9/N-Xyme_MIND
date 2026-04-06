"""Content extractor for code, PDF, DOCX, Markdown files."""

import logging
import os
from pathlib import Path
from typing import Optional, Any

logger = logging.getLogger(__name__)


def detect_encoding(filepath: str) -> str:
    """Detect file encoding by trying common encodings."""
    encodings = ["utf-8", "latin-1", "cp1252", "ascii"]
    for enc in encodings:
        try:
            with open(filepath, "r", encoding=enc) as f:
                f.read(8192)
            return enc
        except (UnicodeDecodeError, UnicodeError):
            continue
    return "utf-8"


def clean_text(text: str, max_chars: int = 50000) -> str:
    """Clean and truncate text."""
    if not text:
        return ""
    # Remove null bytes
    text = text.replace("\x00", "")
    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Truncate
    if len(text) > max_chars:
        text = text[:max_chars] + "\n... [truncated]"
    return text.strip()


def extract_code(filepath: str, max_chars: int = 50000) -> str:
    """Extract text from code files."""
    try:
        encoding = detect_encoding(filepath)
        with open(filepath, "r", encoding=encoding, errors="replace") as f:
            content = f.read()
        return clean_text(content, max_chars)
    except Exception as e:
        logger.debug(f"Failed to read code file {filepath}: {e}")
        return ""


def extract_pdf(filepath: str, max_chars: int = 50000) -> str:
    """Extract text from PDF files."""
    # Try PyMuPDF first
    try:
        import fitz

        doc = fitz.open(filepath)
        text: str = ""
        for page in doc:
            page_text = page.get_text()
            if isinstance(page_text, str):
                text += page_text
            else:
                text += str(page_text) if page_text else ""
            if len(text) > max_chars:
                break
        doc.close()
        return clean_text(text, max_chars)
    except ImportError:
        pass
    except Exception as e:
        logger.debug(f"PyMuPDF failed for {filepath}: {e}")

    # Try pdfplumber
    try:
        import pdfplumber

        text = ""
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
                if len(text) > max_chars:
                    break
        return clean_text(text, max_chars)
    except ImportError:
        pass
    except Exception as e:
        logger.debug(f"pdfplumber failed for {filepath}: {e}")

    logger.debug(f"No PDF library available for {filepath}")
    return ""


def extract_docx(filepath: str, max_chars: int = 50000) -> str:
    """Extract text from DOCX files."""
    try:
        from docx import Document  # type: ignore[import]

        doc = Document(filepath)
        text = "\n".join([p.text for p in doc.paragraphs if p.text])
        return clean_text(text, max_chars)
    except ImportError:
        logger.debug(f"python-docx not available for {filepath}")
        return ""
    except Exception as e:
        logger.debug(f"Failed to read DOCX {filepath}: {e}")
        return ""


def extract_markdown(filepath: str, max_chars: int = 50000) -> str:
    """Extract text from Markdown files."""
    return extract_code(filepath, max_chars)


def extract_config(filepath: str, max_chars: int = 50000) -> str:
    """Extract text from config files."""
    return extract_code(filepath, max_chars)


def extract_content(
    filepath: str, file_type: str = "code", max_chars: int = 50000
) -> str:
    """Extract text content from a file based on its type.

    Args:
        filepath: Path to the file
        file_type: One of 'code', 'doc', 'config', 'document', 'other'
        max_chars: Maximum characters to return

    Returns:
        Extracted text content (may be empty if extraction fails)
    """
    if not os.path.exists(filepath):
        return ""

    try:
        if file_type == "document":
            ext = Path(filepath).suffix.lower()
            if ext == ".pdf":
                return extract_pdf(filepath, max_chars)
            elif ext == ".docx":
                return extract_docx(filepath, max_chars)
        elif file_type == "doc":
            return extract_markdown(filepath, max_chars)
        elif file_type == "config":
            return extract_config(filepath, max_chars)
        elif file_type == "code":
            return extract_code(filepath, max_chars)

        # Fallback: try as text
        return extract_code(filepath, max_chars)
    except Exception as e:
        logger.debug(f"Failed to extract {filepath}: {e}")
        return ""
