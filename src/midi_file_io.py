"""MIDI File IO — Read/write MIDI files"""

import logging
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)


class MIDIFileIO:
    @staticmethod
    def read(path: str) -> Dict:
        try:
            import mido

            mid = mido.MidiFile(path)
            tracks = []
            for track in mid.tracks:
                notes = []
                for msg in track:
                    if msg.type == "note_on":
                        notes.append({"note": msg.note, "velocity": msg.velocity, "time": msg.time})
                tracks.append(notes)
            return {"tracks": tracks, "ticks_per_beat": mid.ticks_per_beat, "type": mid.type}
        except ImportError:
            return {"error": "mido not installed"}

    @staticmethod
    def write(path: str, notes: List[Dict], ticks_per_beat: int = 480):
        try:
            import mido

            mid = mido.MidiFile(ticks_per_beat=ticks_per_beat)
            track = mido.MidiTrack()
            mid.tracks.append(track)
            for note in notes:
                track.append(
                    mido.Message(
                        "note_on",
                        note=note.get("note", 60),
                        velocity=note.get("velocity", 64),
                        time=note.get("time", 0),
                    )
                )
                track.append(
                    mido.Message(
                        "note_off", note=note.get("note", 60), time=note.get("duration", 480)
                    )
                )
            mid.save(path)
            return {"success": True, "output": path}
        except ImportError:
            return {"error": "mido not installed"}
