"""Text wrapping and truncation utilities - Ported from ant-source-code Ink.

This module provides text wrapping and truncation capabilities equivalent to Ink's wrapText function,
adapted for use with the Textual framework.

Usage:
    from tui.hooks import wrap_text, truncate_text
    
    # Wrap text to fit terminal width
    wrapped = wrap_text("Long text...", 40, "wrap")
    
    # Truncate with ellipsis
    truncated = truncate_text("Long text...", 20, "end")
"""

import re
from typing import Literal
from enum import Enum


# Text wrapping styles
class TextWrapStyle(Enum):
    """Text wrapping/truncation styles."""
    WRAP = "wrap"
    WRAP_TRIM = "wrap-trunc"
    TRUNCATE = "truncate"
    TRUNCATE_MIDDLE = "truncate-middle"
    TRUNCATE_START = "truncate-start" 


# Type alias for wrap type
WrapType = Literal["wrap", "wrap-trim", "truncate", "truncate-middle", "truncate-start"]

# ANSI escape code pattern
_ANSICODE_RE = re.compile(r'\x1b\[[0-9;]*m')


# Extended ANSI escape codes (including colors, styles, cursor movements)
_ANSICODE_EXTENDED_RE = re.compile(
    r'\x1b\['
    r'(?:'
    r'[0-9;]*m|'           # SGR ( Select Graphic Rendition )
    r'[0-9;]*;[0-9;]*H|'  # CUP ( Cursor Position )
    r'[0-9;]*A|'          # CUU ( Cursor Up )
    r'[0-9;]*B|'          # CUD ( Cursor Down )
    r'[0-9;]*C|'          # CUF ( Cursor Forward )
    r'[0-9;]*D|'          # CUB ( Cursor Back )
    r'[0-9;]*J|'          # ED ( Erase in Display )
    r'[0-9;]*K|'          # EL ( Erase in Line )
    r'.[0-9a-zA-Z]|'      # Other ESC sequences
    r')'
    r'[0-9a-zA-Z]'        # Final character
)


def ansi_length(text: str) -> int:
    """Calculate the visible length of a string, ignoring ANSI codes.
    
    Args:
        text: Text potentially containing ANSI codes
        
    Returns:
        Length of the text excluding ANSI codes
    """
    return len(ansi_strip(text))


def ansi_strip(text: str) -> str:
    """Remove all ANSI escape codes from text.
    
    Args:
        text: Text potentially containing ANSI codes
        
    Returns:
        Text with all ANSI codes removed
    """
    return _ANSICODE_RE.sub('', text)


def ansi_slice(text: str, start: int, end: int) -> str:
    """Slice text while respecting ANSI codes.
    
    This is more complex than simple stripping because we need to
    account for wide characters (like CJK) that take 2 positions.
    
    Args:
        text: Text to slice
        start: Start position (visual columns)
        end: End position (visual columns)
        
    Returns:
        Sliced text with ANSI codes preserved
    """
    # First, strip to find the actual character positions
    stripped = ansi_strip(text)
    stripped_len = len(stripped)
    
    if start >= stripped_len:
        return ''
    
    # Find start position in original text
    result = []
    visual_pos = 0
    original_pos = 0
    started = False
    
    i = 0
    while i < len(text) and original_pos < end:
        # Check for ANSI code
        if text[i] == '\x1b' and i + 1 < len(text):
            # Find end of ANSI sequence
            j = i + 1
            while j < len(text) and not text[j].isalpha():
                j += 1
            j += 1  # Include the final letter
            
            # Include the full ANSI sequence
            result.append(text[i:j])
            i = j
            continue
        
        # Check if we're in our slice range
        if original_pos >= start:
            started = True
        
        if started:
            result.append(text[i])
        
        # Track visual position
        char = text[i]
        visual_pos += _char_width(char)
        original_pos += 1
        
        if visual_pos >= end:
            break
        
        i += 1
    
    return ''.join(result)


def _char_width(char: str) -> int:
    """Get the display width of a character.
    
    Args:
        char: A single character
        
    Returns:
        2 for wide characters (CJK), 1 otherwise
    """
    # Check for East Asian Wide characters
    code = ord(char)
    
    # CJK Unified Ideographs, Hiragana, Katakana, Hangul
    if (0x4E00 <= code <= 0x9FFF or    # CJK Unified Ideographs
        0x3400 <= code <= 0x4DBF or   # CJK Extension A
        0xF900 <= code <= 0xFAFF or   # CJK Compatibility Ideographs
        0x3040 <= code <= 0x309F or   # Hiragana
        0x30A0 <= code <= 0x30FF or   # Katakana
        0xAC00 <= code <= 0xD7AF):    # Hangul Syllables
        return 2
    
    # Other wide characters (fullwidth forms)
    if 0xFF00 <= code <= 0xFFEF:
        return 2
    
    return 1


def truncate_text(
    text: str,
    columns: int,
    position: Literal["start", "middle", "end"] = "end",
    ellipsis: str = "…",
) -> str:
    """Truncate text to fit within a specified number of columns.
    
    Args:
        text: Text to truncate
        columns: Maximum number of visual columns
        position: Position of ellipsis ("start", "middle", "end")
        ellipsis: Ellipsis character(s) to use
        
    Returns:
        Truncated text with ellipsis if needed
    """
    if columns < 1:
        return ''
    
    if columns == 1:
        return ellipsis
    
    # Get visible length
    length = ansi_length(text)
    if length <= columns:
        return text
    
    # Truncate based on position
    if position == "start":
        # Keep the end
        result = ellipsis + ansi_slice(text, length - columns + 1, length)
        return result
    
    if position == "middle":
        # Keep start and end, add ellipsis in middle
        half = columns // 2
        result = (
            ansi_slice(text, 0, half) +
            ellipsis +
            ansi_slice(text, length - (columns - half) + 1, length)
        )
        return result
    
    # position == "end" (default)
    # Keep the start
    result = ansi_slice(text, 0, columns - 1) + ellipsis
    return result


def wrap_text_ansi(
    text: str,
    max_width: int,
    trim: bool = False,
    hard: bool = True,
) -> list[str]:
    """Wrap text at specified width, respecting ANSI codes.
    
    Args:
        text: Text to wrap
        max_width: Maximum width for each line
        trim: Whether to trim leading/trailing whitespace
        hard: If True, break at exact width; if False, break at word boundaries
        
    Returns:
        List of wrapped lines
    """
    if not text or max_width <= 0:
        return [text] if text else []
    
    lines = []
    current_line = []
    current_width = 0
    
    # Split into words, preserving ANSI codes
    words = _split_into_words(text)
    
    for word in words:
        word_width = ansi_length(word)
        
        # Check if adding this word would exceed width
        if current_width + word_width > max_width:
            # Start a new line
            if current_line:
                line_text = ''.join(current_line)
                if trim:
                    line_text = line_text.strip()
                lines.append(line_text)
            
            # If word is longer than max_width, force break it
            if word_width > max_width:
                # Split the long word
                chunks = _split_long_word(word, max_width)
                for chunk in chunks[:-1]:
                    lines.append(chunk)
                current_line = [chunks[-1]]
                current_width = ansi_length(chunks[-1])
            else:
                current_line = [word]
                current_width = word_width
        else:
            current_line.append(word)
            current_width += word_width
    
    # Add remaining line
    if current_line:
        line_text = ''.join(current_line)
        if trim:
            line_text = line_text.strip()
        lines.append(line_text)
    
    return lines


def _split_into_words(text: str) -> list[str]:
    """Split text into words while preserving whitespace and ANSI codes.
    
    Args:
        text: Text to split
        
    Returns:
        List of words/whitespace segments
    """
    words = []
    current = []
    
    i = 0
    while i < len(text):
        # Check for ANSI code
        if text[i] == '\x1b' and i + 1 < len(text):
            # Flush current buffer
            if current:
                words.append(''.join(current))
                current = []
            
            # Find end of ANSI sequence
            j = i + 1
            while j < len(text) and not text[j].isalpha():
                j += 1
            j += 1  # Include the final letter
            
            # Add the full ANSI sequence
            words.append(text[i:j])
            i = j
            continue
        
        # Check for whitespace - this is a word boundary
        if text[i] in ' \t\n':
            # Flush current buffer
            if current:
                words.append(''.join(current))
                current = []
            
            # Add the whitespace
            words.append(text[i])
            i += 1
            
            # Collapse multiple whitespace to single space
            while i < len(text) and text[i] in ' \t\n':
                i += 1
            continue
        
        # Add character to current word
        current.append(text[i])
        i += 1
    
    # Flush remaining
    if current:
        words.append(''.join(current))
    
    return words


def _split_long_word(word: str, max_width: int) -> list[str]:
    """Split a long word that exceeds max_width.
    
    Args:
        word: Word to split (may contain ANSI codes)
        max_width: Maximum width per chunk
        
    Returns:
        List of chunks
    """
    chunks = []
    current = []
    current_width = 0
    
    i = 0
    while i < len(word):
        # Check for ANSI code
        if word[i] == '\x1b' and i + 1 < len(word):
            # Include ANSI code in current chunk
            j = i + 1
            while j < len(word) and not word[j].isalpha():
                j += 1
            j += 1
            
            current.append(word[i:j])
            i = j
            continue
        
        # Add character
        char = word[i]
        char_width = _char_width(char)
        
        if current_width + char_width > max_width:
            # Start new chunk
            chunks.append(''.join(current))
            current = [char]
            current_width = char_width
        else:
            current.append(char)
            current_width += char_width
        
        i += 1
    
    if current:
        chunks.append(''.join(current))
    
    return chunks


def wrap_text(
    text: str,
    max_width: int,
    wrap_type: WrapType = "wrap",
) -> str:
    """Wrap or truncate text to fit within a maximum width.
    
    This is the main entry point, equivalent to Ink's wrapText function.
    
    Args:
        text: Text to wrap/truncate
        max_width: Maximum width for the output
        wrap_type: Type of wrapping/truncation to apply
        
    Returns:
        Wrapped or truncated text
        
    Example:
        >>> wrap_text("Hello world this is long text", 20, "wrap")
        'Hello world\\nthis is\\nlong text'
        >>> wrap_text("Very long text...", 10, "truncate")
        'Very long…'
    """
    if wrap_type == "wrap":
        lines = wrap_text_ansi(text, max_width, trim=False, hard=True)
        return '\n'.join(lines)
    
    if wrap_type == "wrap-trim":
        lines = wrap_text_ansi(text, max_width, trim=True, hard=True)
        return '\n'.join(lines)
    
    if wrap_type.startswith("truncate"):
        position: Literal["end", "middle", "start"] = "end"
        
        if wrap_type == "truncate-middle":
            position = "middle"
        elif wrap_type == "truncate-start":
            position = "start"
        
        return truncate_text(text, max_width, position)
    
    # Default: return as-is
    return text


def measure_text(text: str) -> int:
    """Measure the visual width of text, accounting for wide characters.
    
    Args:
        text: Text to measure
        
    Returns:
        Visual width in columns
    """
    return ansi_length(text)


def pad_text(
    text: str,
    width: int,
    align: Literal["left", "right", "center"] = "left",
    fill: str = " ",
) -> str:
    """Pad text to a specific width.
    
    Args:
        text: Text to pad
        width: Target width
        align: Alignment direction
        fill: Character to use for padding
        
    Returns:
        Padded text
    """
    text_width = measure_text(text)
    
    if text_width >= width:
        return text
    
    padding = fill * (width - text_width)
    
    if align == "left":
        return text + padding
    elif align == "right":
        return padding + text
    else:  # center
        left_pad = padding[:len(padding) // 2]
        right_pad = padding[len(padding) // 2:]
        return left_pad + text + right_pad