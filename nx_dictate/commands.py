from __future__ import annotations
import logging

logger = logging.getLogger("nxyme_dictate.commands")

COMMANDS = {
    "newline": "\n",
    "new line": "\n",
    "line break": "\n",
    "next line": "\n",
    "period": ".",
    "full stop": ".",
    "dot": ".",
    "comma": ",",
    "question mark": "?",
    "exclamation": "!",
    "exclamation mark": "!",
    "colon": ":",
    "semicolon": ";",
    "dash": "-",
    "hyphen": "-",
    "open paren": "(",
    "close paren": ")",
    "open bracket": "[",
    "close bracket": "]",
    "open quote": '"',
    "close quote": '"',
    "apostrophe": "'",
    "slash": "/",
    "backslash": "\\",
    "tab": "\t",
    "space": " ",
    "indent": "\t",
    "dedent": "",
    "open brace": "{",
    "close brace": "}",
    "at sign": "@",
    "hash": "#",
    "dollar": "$",
    "percent": "%",
    "ampersand": "&",
    "asterisk": "*",
    "plus": "+",
    "equals": "=",
}

SPECIAL_COMMANDS = {
    "capitalize": {"action": "capitalize_next"},
    "capital": {"action": "capitalize_next"},
    "caps": {"action": "all_caps"},
    "all caps": {"action": "all_caps"},
    "allcaps": {"action": "all_caps"},
    "lower case": {"action": "lower_case"},
    "lowercase": {"action": "lower_case"},
    "undo": {"action": "undo"},
    "delete": {"action": "delete_backspace"},
    "backspace": {"action": "delete_backspace"},
    "erase": {"action": "delete_backspace"},
    "remove": {"action": "delete_backspace"},
    "clear": {"action": "clear"},
    "scratch that": {"action": "undo"},
    "forget it": {"action": "undo"},
    "start new sentence": {"action": "capitalize_next"},
    "new sentence": {"action": "capitalize_next"},
    "new paragraph": {"action": "newline_twice"},
    "paragraph": {"action": "newline_twice"},
}

CODING_COMMANDS = {
    "def": "def ",
    "function": "function ",
    "class": "class ",
    "if": "if ",
    "else": "else ",
    "elif": "elif ",
    "for": "for ",
    "while": "while ",
    "return": "return ",
    "import": "import ",
    "from": "from ",
    "print": "print(",
    "console log": "console.log(",
    "log": "log(",
    "async": "async ",
    "await": "await ",
    "try": "try {\n",
    "catch": "} catch (err) {\n",
    "finally": "} finally {\n",
    "self": "self.",
    "this": "this.",
    "const": "const ",
    "let": "let ",
    "var": "var ",
    "type": "type ",
    "interface": "interface ",
    "enum": "enum ",
    "struct": "struct ",
    "pub": "pub ",
    "fn": "fn ",
    "match": "match ",
}

EMOJI_COMMANDS = {
    "smile": "😊",
    "happy": "😊",
    "laugh": "😂",
    "lol": "😂",
    "sad": "😢",
    "cry": "😭",
    "angry": "😠",
    "love": "❤️",
    "heart": "❤️",
    "thumbs up": "👍",
    "thumbs down": "👎",
    "ok": "👌",
    "wave": "👋",
    "bye": "👋",
    "think": "🤔",
    "hmm": "🤔",
    "fire": "🔥",
    "rocket": "🚀",
    "star": "⭐",
    "check": "✅",
    "x": "❌",
    "warning": "⚠️",
    "info": "ℹ️",
    "question": "❓",
}


class CommandRecognizer:
    def __init__(self):
        self._capitalize_next = False
        self._all_caps_mode = False
        self._lower_mode = False

    def process(self, text: str) -> tuple[str, list[str]]:
        if not text:
            return text, []

        applied_commands = []
        result_parts = []
        words = text.split()
        special_action = None

        for word in words:
            lowered = word.lower().strip(".,!?;:()[]\"'")

            if lowered in COMMANDS:
                result_parts.append(COMMANDS[lowered])
                applied_commands.append(lowered)
                continue

            if lowered in SPECIAL_COMMANDS:
                cmd = SPECIAL_COMMANDS[lowered]
                action = cmd["action"]
                applied_commands.append(lowered)

                if action == "capitalize_next":
                    self._capitalize_next = True
                elif action == "all_caps":
                    self._all_caps_mode = not self._all_caps_mode
                elif action == "lower_case":
                    self._lower_mode = True
                elif action in ("delete_backspace", "newline_twice"):
                    special_action = action
                continue

            processed_word = word
            if self._capitalize_next:
                processed_word = word.capitalize()
                self._capitalize_next = False
            elif self._all_caps_mode:
                processed_word = word.upper()
            elif self._lower_mode:
                processed_word = word.lower()

            if result_parts and result_parts[-1] not in " \n":
                result_parts.append(" ")
            result_parts.append(processed_word)

        final_text = "".join(result_parts)
        if special_action:
            return final_text, applied_commands, special_action
        return final_text, applied_commands

    def reset(self):
        self._capitalize_next = False
        self._all_caps_mode = False
        self._lower_mode = False


def create_command_recognizer() -> CommandRecognizer:
    return CommandRecognizer()
