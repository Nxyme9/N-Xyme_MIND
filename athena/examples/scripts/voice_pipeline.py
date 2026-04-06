#!/usr/bin/env python3
"""
Voice Pipeline Module

A complete voice processing pipeline:
- Telegram OGG download
- FFmpeg convert to WAV
- faster-whisper transcription
- Edge TTS response

Target latency: <1 second for transcription
"""

import os
import tempfile
import asyncio
import logging
from pathlib import Path
from typing import Optional, AsyncGenerator
from dataclasses import dataclass

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


@dataclass
class TranscriptionResult:
    """Result from transcription."""

    text: str
    language: Optional[str] = None
    duration: float = 0.0
    segments: list = None


class VoicePipeline:
    """
    Voice processing pipeline for Telegram voice messages.

    Methods:
        download_voice(): Download OGG from Telegram URL
        convert_to_wav(): Convert OGG to WAV using FFmpeg
        transcribe(): Transcribe audio using faster-whisper
        synthesize_speech(): Generate speech using Edge TTS
    """

    def __init__(
        self,
        whisper_model: str = "tiny",
        compute_type: str = "int8",
        language: Optional[str] = None,
        tts_voice: str = "en-US-AriaNeural",
    ):
        """
        Initialize VoicePipeline.

        Args:
            whisper_model: faster-whisper model size (tiny, base, small, medium, large)
            compute_type: Quantization type (int8, float16)
            language: Target language code (None = auto-detect)
            tts_voice: Edge TTS voice name
        """
        self.whisper_model = whisper_model
        self.compute_type = compute_type
        self.language = language
        self.tts_voice = tts_voice

        # Lazy-loaded components
        self._whisper_model = None
        self._vad_model = None

    # =========================================================================
    # Download Methods
    # =========================================================================

    async def download_voice(
        self, url: str, output_path: Optional[Path] = None
    ) -> Path:
        """
        Download OGG audio from Telegram URL.

        Args:
            url: Telegram file URL
            output_path: Output file path (auto-generated if None)

        Returns:
            Path to downloaded OGG file
        """
        import aiohttp

        if output_path is None:
            output_path = Path(tempfile.gettempdir()) / f"voice_{os.getpid()}.ogg"

        logger.info(f"Downloading voice from {url[:50]}...")

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    raise RuntimeError(f"Download failed: HTTP {response.status}")

                content = await response.read()
                with open(output_path, "wb") as f:
                    f.write(content)

        logger.info(f"Downloaded to {output_path}")
        return output_path

    # =========================================================================
    # Conversion Methods
    # =========================================================================

    def convert_to_wav(
        self, ogg_path: Path, output_path: Optional[Path] = None
    ) -> Path:
        """
        Convert OGG to WAV using FFmpeg.

        Args:
            ogg_path: Input OGG file path
            output_path: Output WAV file path (auto-generated if None)

        Returns:
            Path to WAV file
        """
        import subprocess

        if output_path is None:
            output_path = ogg_path.with_suffix(".wav")

        logger.info(f"Converting {ogg_path.name} to WAV...")

        # FFmpeg command: mono, 16kHz for optimal whisper performance
        cmd = [
            "ffmpeg",
            "-y",  # overwrite
            "-i",
            str(ogg_path),
            "-acodec",
            "pcm_s16le",
            "-ar",
            "16000",  # 16kHz for faster-whisper
            "-ac",
            "1",  # mono
            str(output_path),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg failed: {result.stderr}")

        logger.info(f"Converted to {output_path}")
        return output_path

    # =========================================================================
    # Transcription Methods
    # =========================================================================

    def _load_whisper(self):
        """Lazy load faster-whisper model."""
        if self._whisper_model is None:
            try:
                from faster_whisper import WhisperModel

                logger.info(f"Loading faster-whisper model: {self.whisper_model}")
                self._whisper_model = WhisperModel(
                    self.whisper_model, compute_type=self.compute_type
                )
            except ImportError:
                raise ImportError(
                    "faster-whisper not installed. Install with: pip install faster-whisper"
                )
        return self._whisper_model

    def transcribe(
        self, audio_path: Path, language: Optional[str] = None
    ) -> TranscriptionResult:
        """
        Transcribe audio using faster-whisper.

        Args:
            audio_path: Path to audio file (WAV preferred)
            language: Language code (None = auto-detect)

        Returns:
            TranscriptionResult with text and metadata
        """
        model = self._load_whisper()

        lang = language or self.language
        logger.info(f"Transcribing {audio_path.name}...")

        segments, info = model.transcribe(
            str(audio_path),
            language=lang,
            vad_filter=True,  # Enable Silero VAD
            vad_parameters=dict(min_silence_duration_ms=500),
        )

        text_segments = []
        total_duration = 0.0

        for segment in segments:
            text_segments.append(segment.text.strip())
            total_duration = segment.end

        full_text = " ".join(text_segments)

        result = TranscriptionResult(
            text=full_text,
            language=info.language if hasattr(info, "language") else lang,
            duration=total_duration,
            segments=text_segments,
        )

        logger.info(f"Transcribed: {len(full_text)} chars in {total_duration:.2f}s")
        return result

    async def transcribe_async(
        self, audio_path: Path, language: Optional[str] = None
    ) -> TranscriptionResult:
        """
        Async wrapper for transcribe.
        """
        return await asyncio.to_thread(self.transcribe, audio_path, language)

    # =========================================================================
    # TTS Methods
    # =========================================================================

    async def synthesize_speech(
        self, text: str, output_path: Optional[Path] = None, voice: Optional[str] = None
    ) -> Path:
        """
        Synthesize speech using Edge TTS.

        Args:
            text: Text to synthesize
            output_path: Output audio path (auto-generated if None)
            voice: Voice name (default from init)

        Returns:
            Path to generated audio file
        """
        try:
            import edge_tts
        except ImportError:
            raise ImportError(
                "edge-tts not installed. Install with: pip install edge-tts"
            )

        if output_path is None:
            output_path = Path(tempfile.gettempdir()) / f"tts_{os.getpid()}.mp3"

        voice = voice or self.tts_voice
        logger.info(f"Synthesizing with voice {voice}...")

        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(str(output_path))

        logger.info(f"Generated speech: {output_path}")
        return output_path

    async def synthesize_speech_streaming(
        self, text: str, voice: Optional[str] = None
    ) -> AsyncGenerator[bytes, None]:
        """
        Stream synthesized speech in chunks.

        Args:
            text: Text to synthesize
            voice: Voice name

        Yields:
            Audio chunks (MP3)
        """
        try:
            import edge_tts
        except ImportError:
            raise ImportError(
                "edge-tts not installed. Install with: pip install edge-tts"
            )

        voice = voice or self.tts_voice
        communicate = edge_tts.Communicate(text, voice)

        async for chunk in communicate.stream_stream():
            if chunk["type"] == "Audio":
                yield chunk["data"]

    # =========================================================================
    # Pipeline Methods
    # =========================================================================

    async def process_voice_message(
        self, url: str, language: Optional[str] = None
    ) -> TranscriptionResult:
        """
        Full pipeline: download -> convert -> transcribe

        Args:
            url: Telegram voice URL
            language: Target language

        Returns:
            TranscriptionResult
        """
        # Step 1: Download
        ogg_path = await self.download_voice(url)

        try:
            # Step 2: Convert
            wav_path = self.convert_to_wav(ogg_path)

            # Step 3: Transcribe
            result = await self.transcribe_async(wav_path, language)

            return result
        finally:
            # Cleanup temp files
            if ogg_path.exists():
                ogg_path.unlink()
            if Path(str(ogg_path).replace(".ogg", ".wav")).exists():
                Path(str(ogg_path).replace(".ogg", ".wav")).unlink()

    async def generate_voice_response(
        self, text: str, output_path: Optional[Path] = None
    ) -> Path:
        """
        Generate voice response from text.

        Args:
            text: Response text
            output_path: Output path

        Returns:
            Path to audio file
        """
        return await self.synthesize_speech(text, output_path)


# =============================================================================
# Convenience Functions
# =============================================================================


async def quick_transcribe(audio_path: str, model: str = "tiny") -> TranscriptionResult:
    """
    Quick transcription helper.

    Args:
        audio_path: Path to audio file
        model: whisper model size

    Returns:
        TranscriptionResult
    """
    pipeline = VoicePipeline(whisper_model=model)
    return pipeline.transcribe(Path(audio_path))


async def voice_chat(url: str, response_text: str) -> tuple[TranscriptionResult, Path]:
    """
    Complete voice chat: transcribe URL, generate response audio.

    Args:
        url: Telegram voice URL
        response_text: Text to speak

    Returns:
        Tuple of (transcription, response_audio_path)
    """
    pipeline = VoicePipeline()

    # Transcribe
    transcription = await pipeline.process_voice_message(url)

    # Generate response
    response_audio = await pipeline.generate_voice_response(response_text)

    return transcription, response_audio


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Voice Pipeline CLI")
    subparsers = parser.add_subparsers(dest="command")

    # Transcribe command
    transcribe_parser = subparsers.add_parser(
        "transcribe", help="Transcribe audio file"
    )
    transcribe_parser.add_argument("audio", help="Audio file path")
    transcribe_parser.add_argument(
        "--model", default="tiny", choices=["tiny", "base", "small"]
    )

    # Voice chat command
    chat_parser = subparsers.add_parser("chat", help="Voice chat pipeline")
    chat_parser.add_argument("url", help="Telegram voice URL")
    chat_parser.add_argument("--text", required=True, help="Response text")

    args = parser.parse_args()

    if args.command == "transcribe":
        result = asyncio.run(quick_transcribe(args.audio, args.model))
        print(f"\nTranscription:\n{result.text}")
        print(f"\nLanguage: {result.language}")
        print(f"Duration: {result.duration:.2f}s")

    elif args.command == "chat":
        transcription, audio = asyncio.run(voice_chat(args.url, args.text))
        print(f"\nTranscription: {transcription.text}")
        print(f"Response audio: {audio}")

    else:
        parser.print_help()
