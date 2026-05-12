# N-Xyme Dictate - Training/Onboarding Module
# Helps users get started with dictation

from __future__ import annotations

import logging
import json
import os
from dataclasses import dataclass, field
from typing import Optional, Callable

logger = logging.getLogger("nxyme_dictate.training")

# Default config path
DEFAULT_CONFIG_DIR = os.path.expanduser("~/.config/nxyme-dictate")
DEFAULT_CONFIG_FILE = os.path.join(DEFAULT_CONFIG_DIR, "config.json")


@dataclass
class UserProfile:
    """User profile for personalization."""

    name: str = ""
    language: str = "en"
    microphone_name: str = ""
    audio_device_index: int | None = None
    hotkey: str = "ctrl_right"
    model_preference: str = "large-v3-turbo"
    output_method: str = "clipboard"  # clipboard, paste
    sound_enabled: bool = True
    autostart: bool = False

    # Onboarding state
    completed_onboarding: bool = False
    onboarding_step: int = 0
    training_phrase_count: int = 0

    # Usage stats
    total_transcriptions: int = 0
    total_words: int = 0
    average_confidence: float = 0.0


@dataclass
class OnboardingStep:
    """Single onboarding step."""

    title: str
    description: str
    action: str  # "speak", "configure", "test"
    completed: bool = False


class OnboardingGuide:
    """Step-by-step onboarding guide."""

    STEPS = [
        OnboardingStep(
            title="Welcome to N-Xyme Dictation",
            description="Your personal AI-powered voice typing assistant. "
            "This guide will help you get started.",
            action="continue",
        ),
        OnboardingStep(
            title="Microphone Setup",
            description="Make sure your microphone is connected and working. "
            "Speak into the microphone for a moment to test.",
            action="speak",
        ),
        OnboardingStep(
            title="Hotkey Configuration",
            description="The default push-to-talk hotkey is Right Control. "
            "Press and hold the key to record, release to transcribe.",
            action="configure",
        ),
        OnboardingStep(
            title="First Test",
            description="Let's do a quick test. Press your hotkey, say 'Hello world', "
            "and release. Your text should appear!",
            action="speak",
        ),
        OnboardingStep(
            title="Output Settings",
            description="By default, transcribed text is copied to clipboard. "
            "Enable 'paste to active window' for auto-pasting.",
            action="configure",
        ),
        OnboardingStep(
            title="You're Ready!",
            description="That's it! You can now dictate anywhere. "
            "Press your hotkey to start. Happy typing!",
            action="continue",
        ),
    ]

    def __init__(self):
        self._current_step = 0
        self._profile = UserProfile()
        self._load_profile()

    def _load_profile(self):
        """Load user profile from config."""
        try:
            if os.path.exists(DEFAULT_CONFIG_FILE):
                with open(DEFAULT_CONFIG_FILE, "r") as f:
                    data = json.load(f)
                    self._profile = UserProfile(**data)
                    self._current_step = self._profile.onboarding_step
        except Exception as e:
            logger.warning(f"Failed to load profile: {e}")

    def _save_profile(self):
        """Save user profile to config."""
        try:
            os.makedirs(DEFAULT_CONFIG_DIR, exist_ok=True)
            with open(DEFAULT_CONFIG_FILE, "w") as f:
                json.dump(self._profile.__dict__, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save profile: {e}")

    @property
    def current_step(self) -> int:
        return self._current_step

    @property
    def total_steps(self) -> int:
        return len(self.STEPS)

    @property
    def current_step_info(self) -> Optional[OnboardingStep]:
        if 0 <= self._current_step < len(self.STEPS):
            return self.STEPS[self._current_step]
        return None

    @property
    def is_complete(self) -> bool:
        return self._profile.completed_onboarding

    @property
    def profile(self) -> UserProfile:
        return self._profile

    def next_step(self) -> bool:
        """Advance to next step."""
        if self._current_step < len(self.STEPS) - 1:
            self._current_step += 1
            self._profile.onboarding_step = self._current_step
            self._save_profile()
            return True
        return False

    def complete_onboarding(self):
        """Mark onboarding as complete."""
        self._profile.completed_onboarding = True
        self._save_profile()

    def reset(self):
        """Reset onboarding."""
        self._current_step = 0
        self._profile.completed_onboarding = False
        self._profile.onboarding_step = 0
        self._save_profile()

    def update_microphone(self, name: str):
        """Update microphone info."""
        self._profile.microphone_name = name
        self._save_profile()

    def record_transcription(self, word_count: int):
        """Record successful transcription for stats."""
        self._profile.total_transcriptions += 1
        self._profile.total_words += word_count
        self._profile.training_phrase_count += 1
        self._save_profile()


class TrainingMode:
    """Interactive training mode for improving dictation."""

    PRACTICE_PHRASES = [
        "The quick brown fox jumps over the lazy dog",
        "Pack my box with five dozen liquor jugs",
        "How vexingly quick daft zebras jump",
        "Sphinx of black quartz, judge my vow",
        "Two driven jocks help fax my big quiz",
        # Technical phrases for developers
        "def function argument equals return",
        "import system from os path",
        "console dot log bracket open",
        "git commit push origin main",
        "docker compose up dash detach",
        # Common programming terms
        "variable equals string",
        "callback function async await",
        "try catch exception handle",
        "list comprehension generator",
        "decorator context manager",
    ]

    def __init__(self):
        self._current_phrase_index = 0
        self._correct_count = 0
        self._total_attempts = 0

    @property
    def current_phrase(self) -> str:
        return self.PRACTICE_PHRASES[self._current_phrase_index]

    @property
    def progress(self) -> tuple[int, int]:
        """Return (current, total) progress."""
        return (self._current_phrase_index + 1, len(self.PRACTICE_PHRASES))

    @property
    def accuracy(self) -> float:
        if self._total_attempts == 0:
            return 0.0
        return self._correct_count / self._total_attempts

    def next_phrase(self):
        """Move to next phrase."""
        self._current_phrase_index = (self._current_phrase_index + 1) % len(self.PRACTICE_PHRASES)

    def record_attempt(self, success: bool):
        """Record training attempt."""
        self._total_attempts += 1
        if success:
            self._correct_count += 1
            self.next_phrase()

    def reset(self):
        """Reset training."""
        self._current_phrase_index = 0
        self._correct_count = 0
        self._total_attempts = 0


# Singleton
_onboarding: Optional[OnboardingGuide] = None


def get_onboarding() -> OnboardingGuide:
    """Get onboarding guide."""
    global _onboarding
    if _onboarding is None:
        _onboarding = OnboardingGuide()
    return _onboarding


def get_training() -> TrainingMode:
    """Get training mode."""
    return TrainingMode()


def get_user_profile() -> UserProfile:
    """Get user profile."""
    return get_onboarding().profile


def save_settings(
    microphone: str = None,
    hotkey: str = None,
    model: str = None,
    output: str = None,
    sound: bool = None,
    autostart: bool = None,
):
    """Save user settings."""
    guide = get_onboarding()
    profile = guide.profile

    if microphone is not None:
        profile.microphone_name = microphone
    if hotkey is not None:
        profile.hotkey = hotkey
    if model is not None:
        profile.model_preference = model
    if output is not None:
        profile.output_method = output
    if sound is not None:
        profile.sound_enabled = sound
    if autostart is not None:
        profile.autostart = autostart

    guide._save_profile()
    logger.info("Settings saved")
