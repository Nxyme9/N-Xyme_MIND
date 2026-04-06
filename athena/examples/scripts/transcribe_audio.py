#!/usr/bin/env python3
"""
Transcribe Audio - Telegram Voice Message Handler
Wraps whisper_transcription.py for Telegram bot integration.
"""

import os
import sys
import tempfile
import logging
from pathlib import Path

# Add project paths
MIND_DIR = "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND"
sys.path.insert(0, MIND_DIR)

logger = logging.getLogger(__name__)

# Import whisper service
try:
    from src.infrastructure.whisper_transcription import (
        WhisperTranscription,
        TranscriptionResult,
    )

    WHISPER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Whisper not available: {e}")
    WHISPER_AVAILABLE = False

# Global whisper instance
_whisper = None


def get_whisper():
    """Get or create Whisper instance"""
    global _whisper
    if _whisper is None and WHISPER_AVAILABLE:
        try:
            _whisper = WhisperTranscription(model_name="base")
        except Exception as e:
            logger.error(f"Failed to create Whisper: {e}")
    return _whisper


def transcribe_audio(audio_path: str, summarize: bool = False) -> dict:
    """
    Transcribe audio file and optionally summarize.

    Args:
        audio_path: Path to audio file (ogg, wav, mp3, etc.)
        summarize: If True, generate a summary of the transcript

    Returns:
        dict with keys: transcript, summary, language, duration, confidence
    """
    whisper = get_whisper()

    if not whisper:
        return {
            "transcript": "[Whisper not available]",
            "summary": None,
            "language": "en",
            "duration": 0.0,
            "confidence": 0.0,
            "error": "faster-whisper not installed",
        }

    # Check file exists
    if not Path(audio_path).exists():
        return {
            "transcript": "",
            "summary": None,
            "language": "en",
            "duration": 0.0,
            "confidence": 0.0,
            "error": f"File not found: {audio_path}",
        }

    try:
        # Transcribe
        result: TranscriptionResult = whisper.transcribe(audio_path)

        transcript = result.text
        confidence = (
            sum(s.confidence for s in result.segments) / max(len(result.segments), 1)
            if result.segments
            else 0.0
        )

        # Generate summary if requested
        summary = None
        if summarize and transcript:
            summary = generate_summary(transcript)

        return {
            "transcript": transcript,
            "summary": summary,
            "language": result.language,
            "duration": result.duration,
            "confidence": confidence,
            "segments": [
                {
                    "start": s.start,
                    "end": s.end,
                    "text": s.text,
                    "confidence": s.confidence,
                }
                for s in result.segments
            ],
        }

    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        return {
            "transcript": "",
            "summary": None,
            "language": "en",
            "duration": 0.0,
            "confidence": 0.0,
            "error": str(e),
        }


def generate_summary(text: str, max_length: int = 200) -> str:
    """
    Generate a brief summary of the transcript.
    Simple extraction-based summary (no LLM needed).
    """
    if not text:
        return ""

    # Simple extraction: first 2 sentences + key phrases
    sentences = text.split(". ")
    if len(sentences) <= 2:
        return text[:max_length]

    # Take first sentence and a key phrase
    summary = sentences[0]
    if len(sentences) > 1:
        # Find longest sentence as "key" sentence
        key_sentence = max(sentences[1:3], key=len) if len(sentences) > 1 else ""
        if key_sentence and len(key_sentence) < 150:
            summary += ". " + key_sentence

    return summary[:max_length] + "..." if len(summary) > max_length else summary


def is_voice_available() -> bool:
    """Check if voice transcription is available"""
    return WHISPER_AVAILABLE and get_whisper() is not None


# CLI for testing
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Transcribe audio files")
    parser.add_argument("audio_file", help="Path to audio file")
    parser.add_argument("--summarize", action="store_true", help="Generate summary")

    args = parser.parse_args()

    print(f"Transcribing: {args.audio_file}")
    result = transcribe_audio(args.audio_file, summarize=args.summarize)

    print(f"\n--- Result ---")
    print(f"Transcript: {result['transcript'][:500]}...")
    print(f"Language: {result['language']}")
    print(f"Duration: {result['duration']:.2f}s")
    print(f"Confidence: {result['confidence']:.2f}")
    if result.get("summary"):
        print(f"Summary: {result['summary']}")
