from __future__ import annotations
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from text_processor import (
    process_text,
    apply_punctuation,
    apply_capitalization,
    clean_text,
)


class TestCleanText:
    def test_clean_unicode(self):
        result = clean_text("hello\u200bworld")
        assert "\u200b" not in result

    def test_clean_newlines(self):
        result = clean_text("hello\r\nworld")
        assert "\r" not in result and "\n" not in result

    def test_clean_multiple_spaces(self):
        result = clean_text("hello   world")
        assert "  " not in result


class TestApplyPunctuation:
    def test_adds_period(self):
        result = apply_punctuation("hello")
        assert result.endswith(".")

    def test_preserves_existing_period(self):
        result = apply_punctuation("hello.")
        assert result.endswith(".")

    def test_empty_string(self):
        result = apply_punctuation("")
        assert result == ""

    def test_strips_whitespace(self):
        result = apply_punctuation("  hello  ")
        assert result == "hello."


class TestApplyCapitalization:
    def test_first_letter_capitalized(self):
        result = apply_capitalization("hello world")
        assert result[0].isupper()

    def test_abbreviations_uppercase(self):
        result = apply_capitalization("dr smith")
        assert "DR" in result.upper()

    def test_empty_string(self):
        result = apply_capitalization("")
        assert result == ""


class TestProcessText:
    def test_full_process(self):
        result = process_text("hello world", enable_punctuation=True, enable_caps=True)
        assert result.endswith(".")

    def test_disable_punctuation(self):
        result = process_text("hello world", enable_punctuation=False)
        assert not result.endswith(".")

    def test_disable_caps(self):
        result = process_text("hello world", enable_caps=False)
        assert result[0].islower()

    def test_empty_input(self):
        result = process_text("")
        assert result == ""
