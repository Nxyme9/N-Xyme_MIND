from __future__ import annotations
import re
import json
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger("nxyme_dictate.text_processor")

# Default filler words to remove
DEFAULT_FILLERS = {
    "um", "uh", "er", "ah", "like", "you know", "i mean", "sort of",
    "kind of", "basically", "literally", "actually", "honestly",
    "so", "yeah", "okay", "right", "well", "I guess", "I think",
    "maybe", "perhaps", "probably", "possibly", "anyway",
    "anyways", "anyhow", "anyways", "like i said", "as i said",
    "as I was saying", "moving on", "that being said",
    "that said", "in other words", "basically", "essentially",
}

# Mapping of spoken filler phrases to their cleaned equivalents
FILLER_PATTERNS = {
    r"\bokay so\b": "",
    r"\bokay\b": "",
    r"\bso\b": "",
    r"\bthen\b": "",
    r"\byeah\b": "",
    r"\byep\b": "",
    r"\bnope\b": "",
    r"\bI don't know\b": "",
    r"\bi dont know\b": "",
    r"\bhm+\b": "",
    r"\bmm+\b": "",
}


class PersonalDictionary:
    """Personal dictionary for custom words and phrases."""

    def __init__(self, storage_path: Optional[str] = None):
        self._storage_path = storage_path
        self._words: dict[str, str] = {}
        self._load()

    def _load(self):
        if self._storage_path and os.path.exists(self._storage_path):
            try:
                with open(self._storage_path, "r", encoding="utf-8") as f:
                    self._words = json.load(f)
                logger.info(f"Loaded {len(self._words)} words from personal dictionary")
            except Exception as e:
                logger.warning(f"Failed to load personal dictionary: {e}")

    def _save(self):
        if self._storage_path:
            try:
                Path(self._storage_path).parent.mkdir(parents=True, exist_ok=True)
                with open(self._storage_path, "w", encoding="utf-8") as f:
                    json.dump(self._words, f, indent=2, ensure_ascii=False)
                logger.info(f"Saved {len(self._words)} words to personal dictionary")
            except Exception as e:
                logger.warning(f"Failed to save personal dictionary: {e}")

    def add(self, spoken: str, replacement: str):
        """Add a word/phrase to the dictionary."""
        self._words[spoken.lower()] = replacement
        self._save()

    def remove(self, spoken: str):
        """Remove a word/phrase from the dictionary."""
        self._words.pop(spoken.lower(), None)
        self._save()

    def lookup(self, text: str) -> str:
        """Replace known phrases in text."""
        result = text
        for spoken, replacement in self._words.items():
            # Use word boundaries for single words, contains for phrases
            if " " in spoken:
                result = re.sub(re.escape(spoken), replacement, result, flags=re.IGNORECASE)
            else:
                result = re.sub(rf"\b{re.escape(spoken)}\b", replacement, result, flags=re.IGNORECASE)
        return result

    def get_all(self) -> dict[str, str]:
        """Get all dictionary entries."""
        return self._words.copy()


class SnippetsManager:
    """Manages voice shortcuts/snippets."""

    def __init__(self, storage_path: Optional[str] = None):
        self._storage_path = storage_path
        self._snippets: dict[str, str] = {}
        self._load()

    def _load(self):
        if self._storage_path and os.path.exists(self._storage_path):
            try:
                with open(self._storage_path, "r", encoding="utf-8") as f:
                    self._snippets = json.load(f)
                logger.info(f"Loaded {len(self._snippets)} snippets")
            except Exception as e:
                logger.warning(f"Failed to load snippets: {e}")

    def _save(self):
        if self._storage_path:
            try:
                Path(self._storage_path).parent.mkdir(parents=True, exist_ok=True)
                with open(self._storage_path, "w", encoding="utf-8") as f:
                    json.dump(self._snippets, f, indent=2, ensure_ascii=False)
                logger.info(f"Saved {len(self._snippets)} snippets")
            except Exception as e:
                logger.warning(f"Failed to save snippets: {e}")

    def add(self, trigger: str, content: str):
        """Add a snippet."""
        self._snippets[trigger.lower()] = content
        self._save()

    def remove(self, trigger: str):
        """Remove a snippet."""
        self._snippets.pop(trigger.lower(), None)
        self._save()

    def expand(self, text: str) -> str:
        """Expand any snippet triggers in text."""
        result = text
        for trigger, content in self._snippets.items():
            result = re.sub(rf"\b{re.escape(trigger)}\b", content, result, flags=re.IGNORECASE)
        return result

    def get_all(self) -> dict[str, str]:
        """Get all snippets."""
        return self._snippets.copy()


def remove_fillers(text: str) -> str:
    """Remove filler words and phrases from text."""
    if not text:
        return text

    # Remove common filler words (case insensitive)
    for filler in DEFAULT_FILLERS:
        if " " in filler:  # Phrase
            pattern = r"\b" + re.escape(filler) + r"\b"
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)
        else:  # Single word
            text = re.sub(rf"\b{re.escape(filler)}\b", "", text, flags=re.IGNORECASE)

    # Apply additional filler patterns
    for pattern, replacement in FILLER_PATTERNS.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    # Clean up extra spaces from removed words
    text = re.sub(r"\s+", " ", text)
    text = text.strip()

    # Add space after periods that were followed by removed words
    text = re.sub(r"\.\s*\.", ".", text)

    return text


def apply_punctuation(text: str) -> str:
    if not text:
        return text
    text = text.strip()
    if not text:
        return text

    has_end = text.endswith((".", "!", "?"))
    if not has_end:
        text = text.rstrip() + "."

    text = re.sub(r"\s+", " ", text)

    return text


def apply_capitalization(text: str) -> str:
    if not text:
        return text
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return text

    text = text[0].upper() + text[1:] if len(text) > 0 else text

    abbreviations = {
        "dr",
        "mr",
        "mrs",
        "ms",
        "prof",
        "sr",
        "jr",
        "vs",
        "etc",
        "api",
        "cpu",
        "gpu",
        "ram",
        "url",
        "http",
        "https",
        "tcp",
        "ip",
    }

    def cap_word(match):
        word = match.group(0).lower()
        if word in abbreviations:
            return word.upper()
        return word.capitalize()

    text = re.sub(r"\b\w+\b", cap_word, text, flags=re.UNICODE)

    return text


def clean_text(text: str) -> str:
    if not text:
        return text
    text = re.sub(r"[\u200b\u200c\u200d]", "", text)
    text = re.sub(r"[\r\n]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def process_text(
    text: str,
    enable_punctuation: bool = True,
    enable_caps: bool = True,
    enable_fillers: bool = True,
    dictionary: Optional[PersonalDictionary] = None,
    snippets: Optional[SnippetsManager] = None,
) -> str:
    """Process text with all enhancements."""
    text = clean_text(text)
    if not text:
        return text

    # Apply personal dictionary replacements
    if dictionary:
        text = dictionary.lookup(text)

    # Expand snippets
    if snippets:
        text = snippets.expand(text)

    # Remove filler words
    if enable_fillers:
        text = remove_fillers(text)

    # Apply formatting
    if enable_caps:
        text = apply_capitalization(text)
    if enable_punctuation:
        text = apply_punctuation(text)

    return text
