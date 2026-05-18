from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from pydantic import BaseModel, Field


class Backend(str, Enum):
    XDOTOOL = "xdotool"
    WTYPE = "wtype"
    YDOOTOOL = "ydotool"
    CLIPBOARD = "clipboard"


class WhisperModel(str, Enum):
    TINY = "tiny"
    BASE = "base"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    LARGE_V3 = "large-v3"


class AudioConfig(BaseModel):
    device_index: Optional[int] = None
    sample_rate: int = 44100
    channels: int = 1
    chunk_duration: float = 0.05
    silence_threshold: float = 0.01
    silence_duration: float = 0.3
    max_duration: float = 30.0
    normalize: bool = True
    target_db: float = -20.0


class WhisperConfig(BaseModel):
    model: WhisperModel = WhisperModel.BASE
    device: str = "cuda"
    compute_type: str = "float16"
    language: Optional[str] = None
    beam_size: int = 5
    temperature: float = 0.0
    vad_filter: bool = True
    vad_min_silence_duration_ms: int = 500
    vad_speech_pad_ms: int = 200
    initial_prompt: Optional[str] = None


class HotkeyConfig(BaseModel):
    toggle_key: str = "f8"
    hold_key: Optional[str] = "right ctrl"
    backend: str = "evdev"


class InjectionConfig(BaseModel):
    backend: Backend = Backend.XDOTOOL
    delay_ms: int = 10
    chunk_size: int = 50


class CommandConfig(BaseModel):
    enabled: bool = True
    trigger_phrase: str = "command"
    vocabulary: list[str] = Field(default_factory=lambda: [
        "N-Xyme", "Graphiti", "Jarvis", "OpenCode",
        "FastAPI", "Pydantic", "TypeScript", "Playwright",
        "WebSocket", "Tailwind", "CUDA", "Voicemeeter",
        "refactor", "endpoint", "middleware", "frontend", "backend",
    ])
    commands: Dict[str, str] = Field(default_factory=lambda: {
        "new line": "\\n",
        "new paragraph": "\\n\\n",
        "delete last word": "ctrl+backspace",
        "select all": "ctrl+a",
        "copy": "ctrl+c",
        "paste": "ctrl+v",
        "undo": "ctrl+z",
        "redo": "ctrl+shift+z",
        "stop": "STOP_RECORDING",
        "start": "START_RECORDING",
    })


class UIConfig(BaseModel):
    show_tray: bool = True
    sound_enabled: bool = True
    notification_enabled: bool = True
    notification_timeout: int = 3000


class NxDictateConfig(BaseModel):
    audio: AudioConfig = Field(default_factory=AudioConfig)
    whisper: WhisperConfig = Field(default_factory=WhisperConfig)
    hotkey: HotkeyConfig = Field(default_factory=HotkeyConfig)
    injection: InjectionConfig = Field(default_factory=InjectionConfig)
    commands: CommandConfig = Field(default_factory=CommandConfig)
    ui: UIConfig = Field(default_factory=UIConfig)
    config_path: Path = Field(default=Path.home() / ".config" / "nx_dictate" / "config.yaml")

    @classmethod
    def load(cls, path: Optional[Path] = None) -> NxDictateConfig:
        p = path or cls().config_path
        if p.exists():
            with open(p) as f:
                data = yaml.safe_load(f) or {}
            return cls(**data)
        return cls()

    def save(self, path: Optional[Path] = None) -> None:
        p = path or self.config_path
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w") as f:
            yaml.dump(self.model_dump(), f)
