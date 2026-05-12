from __future__ import annotations
import asyncio
import logging
import uuid
from typing import Optional

import aiohttp
from aiohttp import web

logger = logging.getLogger("nxyme_dictate.api")

API_VERSION = "1.0.0"


class DictationAPI:
    def __init__(self, host: str = "0.0.0.0", port: int = 8080):
        self._host = host
        self._port = port
        self._app = web.Application()
        self._engine = None
        self._audio = None
        self._webhook_url: Optional[str] = None
        self._runner: Optional[web.AppRunner] = None

        self._setup_routes()

    def _setup_routes(self):
        self._app.router.add_get("/", self.handle_index)
        self._app.router.add_get("/health", self.handle_health)
        self._app.router.add_post("/transcribe", self.handle_transcribe)
        self._app.router.add_post("/webhook", self.handle_webhook)
        self._app.router.add_get("/stats", self.handle_stats)
        self._app.router.add_post("/config", self.handle_config)
        self._app.router.add_get("/stream", self.handle_stream)

    async def handle_index(self, request):
        return web.json_response(
            {
                "service": "N-Xyme Dictate API",
                "version": API_VERSION,
                "endpoints": [
                    "GET /health",
                    "POST /transcribe",
                    "POST /webhook",
                    "GET /stats",
                    "POST /config",
                ],
            }
        )

    async def handle_health(self, request):
        return web.json_response(
            {
                "status": "healthy",
                "model_loaded": self._engine is not None,
                "version": API_VERSION,
            }
        )

    async def handle_transcribe(self, request):
        try:
            data = await request.json()
            audio_base64 = data.get("audio")
            language = data.get("language", "auto")
            vocabulary = data.get("vocabulary", [])

            if not audio_base64:
                return web.json_response({"error": "No audio data"}, status=400)

            import base64

            audio_bytes = base64.b64decode(audio_base64)
            audio = bytes(audio_bytes)

            audio_array = self._audio_preprocessor(audio) if self._audio else None

            prompt = " ".join(vocabulary) if vocabulary else None
            result = self._engine.transcribe(audio_array, language=language, initial_prompt=prompt)

            response = {
                "text": result,
                "id": str(uuid.uuid4()),
            }

            if self._webhook_url:
                asyncio.create_task(self._send_webhook(response))

            return web.json_response(response)

        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def handle_webhook(self, request):
        data = await request.json()
        url = data.get("url")
        if url:
            self._webhook_url = url
            return web.json_response({"status": "webhook configured", "url": url})
        return web.json_response({"error": "No URL provided"}, status=400)

    async def handle_stats(self, request):
        from .stats import get_monitor

        monitor = get_monitor()
        stats = monitor.get_stats()
        return web.json_response(stats)

    async def handle_config(self, request):
        data = await request.json()
        return web.json_response({"status": "config updated", "config": data})

    async def _send_webhook(self, data):
        try:
            async with aiohttp.ClientSession() as session:
                await session.post(self._webhook_url, json=data)
        except Exception as e:
            logger.error(f"Webhook failed: {e}")

    def _audio_preprocessor(self, audio_bytes):
        import numpy as np

        audio = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        from .audio_processing import preprocess_audio

        return preprocess_audio(audio)

    def set_engine(self, engine, audio_processor=None):
        self._engine = engine
        self._audio = audio_processor

    async def start(self):
        self._runner = web.AppRunner(self._app)
        await self._runner.setup()
        site = web.TCPSite(self._runner, self._host, self._port)
        await site.start()
        logger.info(f"API server started on {self._host}:{self._port}")

    async def stop(self):
        if self._runner:
            await self._runner.cleanup()

    async def handle_stream(self, request):
        async def event_generator():
            while True:
                await asyncio.sleep(1)
                yield {"event": "ping", "data": "ok"}

        return web.StreamingResponse(
            event_generator(),
            content_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        )


_api: Optional[DictationAPI] = None


def get_api(host: str = "0.0.0.0", port: int = 8080) -> DictationAPI:
    global _api
    if _api is None:
        _api = DictationAPI(host, port)
    return _api
