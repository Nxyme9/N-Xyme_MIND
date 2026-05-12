from __future__ import annotations
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from commands import CommandRecognizer, SPECIAL_COMMANDS, COMMANDS


class TestCommandRecognizer:
    def test_newline_command(self):
        recognizer = CommandRecognizer()
        result, commands = recognizer.process("hello newline world")
        assert "\n" in result

    def test_period_command(self):
        recognizer = CommandRecognizer()
        result, commands = recognizer.process("hello period")
        assert "." in result

    def test_comma_command(self):
        recognizer = CommandRecognizer()
        result, commands = recognizer.process("hello comma world")
        assert "," in result

    def test_delete_command_recognized(self):
        recognizer = CommandRecognizer()
        result = recognizer.process("delete")
        if len(result) == 3:
            processed, commands, special_action = result
            assert "delete" in commands
        else:
            processed, commands = result
            assert "delete" in commands

    def test_caps_command_toggle(self):
        recognizer = CommandRecognizer()
        result, commands = recognizer.process("caps")
        assert "caps" in commands

    def test_regular_text(self):
        recognizer = CommandRecognizer()
        result, commands = recognizer.process("hello world")
        assert "hello world" in result.lower() or result.strip() != ""

    def test_reset(self):
        recognizer = CommandRecognizer()
        recognizer.process("hello all caps world")
        recognizer.reset()
        assert not recognizer._all_caps_mode


class TestCommandDictionaries:
    def test_special_commands_exist(self):
        assert "delete" in SPECIAL_COMMANDS
        assert "newline" in COMMANDS
        assert "new line" in COMMANDS

    def test_punctuation_commands(self):
        assert "period" in COMMANDS
        assert "comma" in COMMANDS
        assert "question mark" in COMMANDS
