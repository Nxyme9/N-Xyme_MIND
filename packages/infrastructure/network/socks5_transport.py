"""
SOCKS5 Transport for httpx.AsyncClient
Routes HTTP requests through SOCKS5 proxy using httpx native support.
"""

import httpx
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.core.backend import Backend


class SOCKS5Transport:
    """Custom httpx transport that routes requests through SOCKS5 proxy."""

    def __init__(self, backend: "Backend"):
        self.backend = backend
        self.proxy_url = f"socks5://{backend.socks_host}:{backend.socks_port}"
        self._client: "httpx.AsyncClient | None" = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                proxy=self.proxy_url,
                timeout=httpx.Timeout(120.0),
            )
        return self._client

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        client = await self._get_client()
        try:
            response = await client.send(request)
            self.backend.request_count += 1
            return response
        except Exception:
            self.backend.error_count += 1
            raise

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
