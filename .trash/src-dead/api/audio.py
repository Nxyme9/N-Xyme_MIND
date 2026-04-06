"""Audio API endpoints for voice I/O."""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
import subprocess
import asyncio
import edge_tts
from datetime import datetime

router = APIRouter(prefix="/audio", tags=["audio"])

VLC_PATH = r"C:\Program Files\VideoLAN\VLC\vlc.exe"
OUTPUT_DIR = Path("data/narrations")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class NarrateRequest(BaseModel):
    text: str
    voice: str = "es-ES-AlvaroNeural"
    auto_play: bool = True


class PlayRequest(BaseModel):
    file_path: str


@router.post("/generate")
async def generate_audio(req: NarrateRequest):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"narration_{timestamp}_{req.voice}.wav"
    output = OUTPUT_DIR / filename

    communicate = edge_tts.Communicate(req.text, req.voice)
    await communicate.save(str(output))

    if req.auto_play:
        _play_audio(str(output))

    return {"status": "ok", "file": str(output), "voice": req.voice}


@router.post("/play")
async def play_audio(req: PlayRequest):
    if not Path(req.file_path).exists():
        return {"status": "error", "error": "File not found"}
    _play_audio(req.file_path)
    return {"status": "ok", "file": req.file_path}


@router.get("/list")
async def list_audio():
    files = sorted(OUTPUT_DIR.glob("*.wav"), key=lambda f: f.stat().st_mtime, reverse=True)
    return [{"name": f.name, "path": str(f), "size": f.stat().st_size, "modified": f.stat().st_mtime} for f in files[:20]]


@router.get("/voices")
async def list_voices():
    return [
        {"id": "es-ES-AlvaroNeural", "name": "Alvaro (Spanish)", "lang": "es"},
        {"id": "es-ES-ElviraNeural", "name": "Elvira (Spanish)", "lang": "es"},
        {"id": "en-GB-RyanNeural", "name": "Ryan (British)", "lang": "en"},
        {"id": "en-US-GuyNeural", "name": "Guy (American)", "lang": "en"},
        {"id": "en-US-JennyNeural", "name": "Jenny (American)", "lang": "en"},
    ]


def _play_audio(filepath: str):
    if Path(VLC_PATH).exists():
        subprocess.Popen([VLC_PATH, "--play-and-exit", filepath], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        ps_cmd = f'(New-Object Media.SoundPlayer "{filepath}").PlaySync()'
        subprocess.Popen(["powershell", "-Command", ps_cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
