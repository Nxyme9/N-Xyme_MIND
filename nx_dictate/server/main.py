#!/usr/bin/env python3
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import asyncio
import websockets
import json
import base64
import logging
import numpy as np
from nx_engine.engine.whisper import WhisperClient
from nx_dictate.injection import copy_and_paste

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("nxyme-ws")

MODEL = "deepdml/faster-whisper-large-v3-turbo-ct2"
DEVICE = 1
SAMPLE_RATE = 16000


class DictateServer:
    def __init__(self, host="0.0.0.0", port=8765):
        self.host = host
        self.port = port
        self.whisper = None
        self.is_recording = False
        self.audio_buffer = []

    async def start(self):
        logger.info(f"Loading Whisper {MODEL}...")
        self.whisper = WhisperClient(model=MODEL, device="cuda", compute_type="float16")
        logger.info("Whisper ready")
        logger.info(f"Starting WebSocket server on {self.host}:{self.port}")
        async with websockets.serve(self.handle_client, self.host, self.port):
            await asyncio.Future()

    async def handle_client(self, websocket):
        client_id = id(websocket)
        logger.info(f"Client connected: {client_id}")

        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    msg_type = data.get("type")

                    if msg_type == "start":
                        await self._handle_start(websocket, data)
                    elif msg_type == "stop":
                        await self._handle_stop(websocket, data)
                    elif msg_type == "audio":
                        await self._handle_audio(websocket, data)
                    elif msg_type == "stream":
                        await self._handle_stream(websocket, data)
                    elif msg_type == "ping":
                        await websocket.send(json.dumps({"type": "pong"}))
                    else:
                        await websocket.send(
                            json.dumps({"type": "error", "message": f"Unknown message type: {msg_type}"}))
                except json.JSONDecodeError:
                    await websocket.send(json.dumps({"type": "error", "message": "Invalid JSON"}))

        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client disconnected: {client_id}")

    async def _handle_start(self, websocket, data):
        self.is_recording = True
        self.audio_buffer = []
        device = data.get("device", DEVICE)
        logger.info(f"Recording started for client, device: {device}")
        await websocket.send(json.dumps({"type": "started", "device": device, "sample_rate": SAMPLE_RATE}))

    async def _handle_stop(self, websocket, data):
        self.is_recording = False

        if not self.audio_buffer:
            await websocket.send(json.dumps({"type": "error", "message": "No audio recorded"}))
            return

        audio = np.concatenate(self.audio_buffer)
        self.audio_buffer = []

        await websocket.send(json.dumps({"type": "transcribing", "duration": len(audio) / SAMPLE_RATE}))

        result = self.whisper.transcribe(audio)

        paste = data.get("paste", False)
        if paste and result:
            copy_and_paste(result)

        await websocket.send(json.dumps({"type": "result", "text": result, "paste": paste}))

    async def _handle_audio(self, websocket, data):
        if not self.is_recording:
            return

        try:
            audio_bytes = base64.b64decode(data["data"])
            audio = np.frombuffer(audio_bytes, dtype=np.float32)
            self.audio_buffer.append(audio)
        except Exception as e:
            logger.error(f"Audio decode error: {e}")

    async def _handle_stream(self, websocket, data):
        try:
            audio_bytes = base64.b64decode(data["data"])
            audio = np.frombuffer(audio_bytes, dtype=np.float32)
            
            result = self.whisper.transcribe(audio, beam_size=1, temperature=0.0)
            
            if result:
                await websocket.send(json.dumps({
                    "type": "partial",
                    "text": result,
                    "timestamp": data.get("timestamp", 0)
                }))
        except Exception as e:
            logger.error(f"Stream error: {e}")


async def main():
    import argparse
    parser = argparse.ArgumentParser(description="N-Xyme Dictate WebSocket Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind")
    parser.add_argument("-p", "--port", type=int, default=8765, help="Port to bind")
    args = parser.parse_args()

    server = DictateServer(host=args.host, port=args.port)
    await server.start()


if __name__ == "__main__":
    asyncio.run(main())
