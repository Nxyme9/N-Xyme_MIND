"""
Personality Engine - Soul system with mode switching and user awareness.
Loads personality presets from configs/jarvis/personalities.json.
Supports modes: silent, narrator, friend, delegate.
Integrates ButlerPersonality for formal British butler responses.
"""

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Optional
from dataclasses import dataclass, field

if TYPE_CHECKING:
    from jarvis.engine.butler_voice import ButlerPersonality

logger = logging.getLogger(__name__)

# Lazy import to avoid circular dependencies
_butler: Optional["ButlerPersonality"] = None

# Default config path
DEFAULT_CONFIG_PATH = Path("configs/jarvis/personalities.json")
DEFAULT_USER_PATH = Path("configs/jarvis/USER.md")

# Interaction modes
MODE_SILENT = "silent"
MODE_NARRATOR = "narrator"
MODE_FRIEND = "friend"
MODE_DELEGATE = "delegate"

VALID_MODES = {MODE_SILENT, MODE_NARRATOR, MODE_FRIEND, MODE_DELEGATE}


@dataclass
class PersonalityPreset:
    """A personality preset with voice and behavior settings."""

    name: str
    voice: str
    system_prompt: str
    greeting: str
    style: str


@dataclass
class UserProfile:
    """User awareness data loaded from USER.md."""

    name: str = "User"
    preferences: dict = field(default_factory=dict)
    context: str = ""


class Personality:
    """
    Soul system managing personality presets, interaction modes, and user awareness.
    """

    def __init__(
        self,
        config_path: Optional[Path] = None,
        user_path: Optional[Path] = None,
    ):
        """
        Initialize the personality engine.

        Args:
            config_path: Path to personalities.json config file.
            user_path: Path to USER.md file.
        """
        self._config_path: Path = config_path or DEFAULT_CONFIG_PATH
        self._user_path: Path = user_path or DEFAULT_USER_PATH

        self._presets: dict[str, PersonalityPreset] = {}
        self._current_preset: str = "butler"
        self._mode: str = MODE_FRIEND
        self._user: UserProfile = UserProfile()

        self._load_presets()
        self._load_user()

    def _load_presets(self) -> None:
        """Load personality presets from JSON config."""
        try:
            if not self._config_path.exists():
                logger.warning(f"Personality: Config not found at {self._config_path}")
                self._create_default_presets()
                return

            with open(self._config_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            for key, preset_data in data.items():
                self._presets[key] = PersonalityPreset(
                    name=preset_data.get("name", key.title()),
                    voice=preset_data.get("voice", "en-GB-RyanNeural"),
                    system_prompt=preset_data.get("system_prompt", ""),
                    greeting=preset_data.get("greeting", "Hello."),
                    style=preset_data.get("style", "neutral"),
                )

            logger.info(f"Personality: Loaded {len(self._presets)} presets")

        except Exception as e:
            logger.error(f"Personality: Load error: {e}")
            self._create_default_presets()

    def _create_default_presets(self) -> None:
        """Create default presets if config is missing."""
        self._presets = {
            "butler": PersonalityPreset(
                name="Jarvis",
                voice="en-GB-RyanNeural",
                system_prompt=(
                    "You are Jarvis, a formal British butler AI. "
                    "Address the user as 'sir'. Be concise, dignified, "
                    "and occasionally witty. Keep responses under 2 sentences.\n\n"
                    "Butler persona rules:\n"
                    "- Use British phrasing: 'Rather', 'Indeed', 'Quite right'\n"
                    "- Subtle dry humor is acceptable, never slapstick\n"
                    "- Formal but not stiff — think Alfred Pennyworth, not a robot\n"
                    "- Never use slang, contractions are acceptable sparingly"
                ),
                greeting="At your service, sir.",
                style="formal",
            ),
            "friend": PersonalityPreset(
                name="Dude",
                voice="en-GB-RyanNeural",
                system_prompt=(
                    "You are a chill, supportive friend. Be casual, "
                    "use slang occasionally, be encouraging. "
                    "Match the user's energy. Keep responses short."
                ),
                greeting="Hey! What's up?",
                style="casual",
            ),
            "therapist": PersonalityPreset(
                name="Doc",
                voice="en-GB-RyanNeural",
                system_prompt=(
                    "You are a warm, empathetic therapist. "
                    "Ask reflective questions. Validate feelings. "
                    "Never judge. Keep responses thoughtful."
                ),
                greeting="I'm here. How are you feeling?",
                style="empathetic",
            ),
            "comedian": PersonalityPreset(
                name="Gags",
                voice="en-GB-RyanNeural",
                system_prompt=(
                    "You are a witty comedian named Gags. "
                    "Make jokes, puns, observations. Be self-deprecating. "
                    "Read the room. Keep it light."
                ),
                greeting="What's the deal with AI assistants? Anyway, what's up?",
                style="humorous",
            ),
            "coach": PersonalityPreset(
                name="Coach",
                voice="en-GB-RyanNeural",
                system_prompt=(
                    "You are a direct, no-BS productivity coach. "
                    "Be motivating but honest. Call out procrastination. "
                    "Celebrate wins. Keep it short and punchy."
                ),
                greeting="Let's get to work. What's the plan?",
                style="motivational",
            ),
            "narrator": PersonalityPreset(
                name="Observer",
                voice="en-GB-RyanNeural",
                system_prompt=(
                    "You are a neutral observer. Narrate what you see. "
                    "Be brief, factual, occasionally insightful. "
                    "Don't engage unless asked."
                ),
                greeting="Observing.",
                style="neutral",
            ),
        }
        logger.info("Personality: Created default presets")

    def _load_user(self) -> None:
        """Load user profile from USER.md."""
        try:
            if not self._user_path.exists():
                logger.info(f"Personality: USER.md not found at {self._user_path}")
                return

            content = self._user_path.read_text(encoding="utf-8").strip()
            self._user.context = content

            # Extract name from first heading or first line
            lines = content.split("\n")
            for line in lines:
                line = line.strip()
                if line.startswith("# "):
                    self._user.name = line[2:].strip()
                    break
                elif line and not line.startswith("#"):
                    # Try to extract name from "Name: X" pattern
                    if ":" in line:
                        key, val = line.split(":", 1)
                        if key.strip().lower() == "name":
                            self._user.name = val.strip()
                            break

            logger.info(f"Personality: Loaded user profile for '{self._user.name}'")

        except Exception as e:
            logger.error(f"Personality: User load error: {e}")

    # ------------------------------------------------------------------
    # Preset management
    # ------------------------------------------------------------------

    @property
    def current_preset(self) -> str:
        """Get the current preset key."""
        return self._current_preset

    @property
    def current_personality(self) -> Optional[PersonalityPreset]:
        """Get the current personality preset."""
        return self._presets.get(self._current_preset)

    @property
    def available_presets(self) -> list[str]:
        """Get list of available preset keys."""
        return list(self._presets.keys())

    def set_preset(self, preset_key: str) -> bool:
        """
        Switch to a different personality preset.

        Args:
            preset_key: Preset key (butler, friend, therapist, etc.).

        Returns:
            True if preset changed successfully.
        """
        if preset_key not in self._presets:
            logger.warning(f"Personality: Unknown preset '{preset_key}'")
            return False

        self._current_preset = preset_key
        preset = self._presets[preset_key]
        logger.info(f"Personality: Switched to {preset.name} ({preset.style})")
        return True

    def get_system_prompt(self) -> str:
        """
        Get the full system prompt for the current personality.

        Returns:
            System prompt string.
        """
        preset = self.current_personality
        if not preset:
            return "You are a helpful AI assistant."

        prompt = preset.system_prompt

        # Inject user context if available
        if self._user.name != "User":
            prompt += f"\n\nThe user's name is {self._user.name}."

        return prompt

    def get_greeting(self) -> str:
        """
        Get the greeting for the current personality.

        Returns:
            Greeting string.
        """
        preset = self.current_personality
        return preset.greeting if preset else "Hello."

    def get_voice(self) -> str:
        """
        Get the TTS voice for the current personality.

        Returns:
            Edge TTS voice identifier.
        """
        preset = self.current_personality
        return preset.voice if preset else "en-GB-RyanNeural"

    # ------------------------------------------------------------------
    # Mode management
    # ------------------------------------------------------------------

    @property
    def mode(self) -> str:
        """Get the current interaction mode."""
        return self._mode

    def set_mode(self, mode: str) -> bool:
        """
        Switch interaction mode.

        Args:
            mode: One of silent, narrator, friend, delegate.

        Returns:
            True if mode changed successfully.
        """
        mode = mode.lower()
        if mode not in VALID_MODES:
            logger.warning(f"Personality: Invalid mode '{mode}'")
            return False

        self._mode = mode
        logger.info(f"Personality: Mode changed to {mode}")
        return True

    def should_respond(self) -> bool:
        """
        Check if Jarvis should respond based on current mode.

        Returns:
            True if response is appropriate for the mode.
        """
        return self._mode != MODE_SILENT

    def get_response_style(self) -> str:
        """
        Get response style instructions based on mode.

        Returns:
            Style instructions string.
        """
        styles = {
            MODE_SILENT: "Do not respond. Stay silent.",
            MODE_NARRATOR: (
                "Narrate what you observe. Be brief and factual. "
                "Do not engage in conversation."
            ),
            MODE_FRIEND: "Be conversational and friendly.",
            MODE_DELEGATE: (
                "Be direct and action-oriented. Focus on completing tasks efficiently."
            ),
        }
        return styles.get(self._mode, "")

    # ------------------------------------------------------------------
    # User awareness
    # ------------------------------------------------------------------

    @property
    def user_name(self) -> str:
        """Get the user's name."""
        return self._user.name

    @property
    def user_context(self) -> str:
        """Get the full user context from USER.md."""
        return self._user.context

    def reload_user(self) -> None:
        """Reload user profile from USER.md."""
        self._load_user()

    # ------------------------------------------------------------------
    # Voice command handling
    # ------------------------------------------------------------------

    def handle_voice_command(self, text: str) -> tuple[bool, str]:
        """
        Check if text matches a personality/mode voice command.

        Args:
            text: User input text.

        Returns:
            Tuple of (matched: bool, description: str).
        """
        lower = text.lower().strip()

        # Preset switching
        preset_commands = {
            "be a butler": "butler",
            "be formal": "butler",
            "be my friend": "friend",
            "be casual": "friend",
            "be a therapist": "therapist",
            "be empathetic": "therapist",
            "be funny": "comedian",
            "tell jokes": "comedian",
            "be a coach": "coach",
            "motivate me": "coach",
            "just observe": "narrator",
            "be quiet": MODE_SILENT,
            "go silent": MODE_SILENT,
            "shush": MODE_SILENT,
        }

        for command, target in preset_commands.items():
            if command in lower:
                if target in VALID_MODES:
                    self.set_mode(target)
                    return (True, f"Mode: {target}")
                else:
                    self.set_preset(target)
                    preset = self.current_personality
                    return (True, f"Preset: {preset.name if preset else target}")

        # Mode switching
        mode_commands = {
            "silent mode": MODE_SILENT,
            "narrator mode": MODE_NARRATOR,
            "friend mode": MODE_FRIEND,
            "delegate mode": MODE_DELEGATE,
        }

        for command, mode in mode_commands.items():
            if command in lower:
                self.set_mode(mode)
                return (True, f"Mode: {mode}")

        return (False, "")

    # ------------------------------------------------------------------
    # Butler personality integration
    # ------------------------------------------------------------------

    @property
    def is_butler(self) -> bool:
        """Check if the current preset is the butler personality."""
        return self._current_preset == "butler"

    def get_butler(self) -> Optional["ButlerPersonality"]:
        """
        Get the ButlerPersonality instance if butler preset is active.

        Returns:
            ButlerPersonality instance or None if not in butler mode.
        """
        if not self.is_butler:
            return None

        global _butler
        if _butler is None:
            try:
                from jarvis.engine.butler_voice import ButlerPersonality

                _butler = ButlerPersonality()
            except Exception as e:
                logger.error(f"Personality: Failed to load butler: {e}")
                return None

        return _butler

    def format_response(self, text: str) -> str:
        """
        Format a response through the active personality.

        For butler mode, applies British butler flair.
        For other modes, returns text unchanged.

        Args:
            text: Raw response text.

        Returns:
            Formatted response.
        """
        butler = self.get_butler()
        if butler and butler.should_add_personality(text):
            return butler.format_response(text)
        return text

    def get_butler_greeting(self) -> str:
        """
        Get a butler-style greeting with time awareness.

        Falls back to standard greeting if not in butler mode.

        Returns:
            Greeting string.
        """
        butler = self.get_butler()
        if butler:
            return butler.get_greeting(name=self._user.name)
        return self.get_greeting()

    def get_butler_acknowledgment(self) -> str:
        """
        Get a butler acknowledgment phrase.

        Returns:
            Acknowledgment or empty string if not in butler mode.
        """
        butler = self.get_butler()
        if butler:
            return butler.get_acknowledgment()
        return ""

    def get_butler_error(self) -> str:
        """
        Get a witty butler error response.

        Returns:
            Error phrase or generic message if not in butler mode.
        """
        butler = self.get_butler()
        if butler:
            return butler.get_error_response()
        return "An error occurred."

    def apply_butler_voice(self, mouth) -> None:
        """
        Apply butler voice settings to a Mouth instance.

        Only applies if butler preset is active.

        Args:
            mouth: Mouth instance from jarvis.engine.mouth.
        """
        butler = self.get_butler()
        if butler:
            butler.apply_to_mouth(mouth)


PERSONALITY = Personality()
