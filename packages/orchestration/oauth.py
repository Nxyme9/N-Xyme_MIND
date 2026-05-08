"""
OAuth 2.0 Support — Authorization code flow with PKCE.

Ported from: services/oauth/* (Claude Code)
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import secrets
import threading
import time
import urllib.parse
import webbrowser
from dataclasses import dataclass
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Any, Callable, Optional
from urllib.request import urlopen
from urllib.error import URLError

logger = logging.getLogger(__name__)


@dataclass
class OAuthTokens:
    """OAuth tokens from flow."""
    access_token: str
    refresh_token: str
    expires_at: float
    scopes: list[str]
    subscription_type: Optional[str] = None
    rate_limit_tier: Optional[str] = None
    profile: Optional[dict] = None
    token_account: Optional[dict] = None


def generate_code_verifier() -> str:
    """Generate PKCE code verifier (43-128 chars, URL-safe)."""
    return secrets.token_urlsafe(32)


def generate_code_challenge(verifier: str) -> str:
    """Generate PKCE code challenge from verifier (S256 method)."""
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).decode().rstrip("=")


def generate_state() -> str:
    """Generate OAuth state parameter."""
    return secrets.token_urlsafe(16)


class AuthCodeListener:
    """Local HTTP server to receive OAuth callback."""

    def __init__(self, port: int = 0):
        self.port = port
        self.server: Optional[HTTPServer] = None
        self.auth_code: Optional[str] = None
        self.state: Optional[str] = None
        self._pending_response: threading.Event = threading.Event()
        self._lock = threading.Lock()

    def start(self) -> int:
        """Start the listener on a free port."""
        if self.server:
            return self.port

        for attempt in range(9000, 9100):
            try:
                self.port = attempt
                self.server = HTTPServer(("127.0.0.1", self.port), _AuthHandler)
                self.server.app = self
                thread = threading.Thread(target=self.server.serve_forever, daemon=True)
                thread.start()
                logger.info(f"OAuth listener started on port {self.port}")
                return self.port
            except OSError:
                continue

        raise RuntimeError("No free port found for OAuth listener")

    def wait_for_authorization(
        self,
        state: str,
        on_ready: Callable[[], Any],
    ) -> str:
        """Wait for authorization code."""
        self.state = state
        on_ready()

        if not self._pending_response.wait(timeout=300):
            raise TimeoutError("OAuth flow timed out")

        if not self.auth_code:
            raise RuntimeError("No authorization code received")

        return self.auth_code

    def has_pending_response(self) -> bool:
        """Check if automatic flow response is pending."""
        return self._pending_response.is_set() and self.auth_code is not None

    def handle_success_redirect(self, scopes: list[str]) -> None:
        """Send success redirect to browser."""
        if self.server:
            try:
                redirect_url = f"http://127.0.0.1:{self.port}/success?scopes={urllib.parse.quote(','.join(scopes))}"
                urlopen(redirect_url, timeout=5)
            except URLError:
                pass

    def handle_error_redirect(self) -> None:
        """Send error redirect to browser."""
        if self.server:
            try:
                urlopen(f"http://127.0.0.1:{self.port}/error", timeout=5)
            except URLError:
                pass

    def close(self) -> None:
        """Stop the server."""
        if self.server:
            self.server.shutdown()
            self.server = None


class _AuthHandler(BaseHTTPRequestHandler):
    """Handler for OAuth callback."""

    def do_GET(self) -> None:
        app: AuthCodeListener = self.server.app  # type: ignore[attr-defined]
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)

        if parsed.path == "/callback":
            code = query.get("code", [None])[0]
            state = query.get("state", [None])[0]

            if code and state == app.state:
                app.auth_code = code
                app._pending_response.set()
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(b"<html><body><h1>Success!</h1></body></html>")
            else:
                self.send_response(400)
                self.end_headers()

        elif parsed.path == "/success":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html><body><h1>Linked!</h1></body></html>")

        elif parsed.path == "/error":
            self.send_response(400)
            self.end_headers()

    def log_message(self, format: str, *args: Any) -> None:
        pass


def build_auth_url(
    code_challenge: str,
    state: str,
    port: int,
    is_manual: bool = False,
    **opts: Any,
) -> str:
    """Build OAuth authorization URL."""
    client_id = os.environ.get("OAUTH_CLIENT_ID", "cli")
    redirect_uri = f"http://127.0.0.1:{port}/callback"

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "read:user write:organization",
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }

    if opts.get("loginWithClaudeAi"):
        params["login_hint"] = "claude.ai"

    if opts.get("inferenceOnly"):
        params["scope"] = "read:user"

    base_url = os.environ.get(
        "OAUTH_AUTH_URL",
        "https://auth.anthropic.com/oauth/authorize"
    )

    if is_manual:
        base_url = os.environ.get(
            "OAUTH_MANUAL_AUTH_URL",
            "https://auth.anthropic.com/oauth/authorize/manual"
        )

    return f"{base_url}?{urllib.parse.urlencode(params)}"


def exchange_code_for_tokens(
    code: str,
    state: str,
    code_verifier: str,
    port: int,
    is_manual: bool = False,
    expires_in: int = 86400,
) -> dict[str, Any]:
    """Exchange authorization code for tokens."""
    token_url = os.environ.get(
        "OAUTH_TOKEN_URL",
        "https://auth.anthropic.com/oauth/token"
    )

    data = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": os.environ.get("OAUTH_CLIENT_ID", "cli"),
        "redirect_uri": f"http://127.0.0.1:{port}/callback",
        "code_verifier": code_verifier,
    }

    if is_manual:
        data["grant_type"] = "authorization_code_manual"

    request = urllib.request.Request(
        token_url,
        data=urllib.parse.urlencode(data).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode())


def fetch_profile_info(access_token: str) -> dict[str, Any]:
    """Fetch user profile information."""
    profile_url = os.environ.get("OAUTH_PROFILE_URL", "https://api.anthropic.com/me")

    request = urllib.request.Request(profile_url)
    request.add_header("Authorization", f"Bearer {access_token}")

    try:
        with urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode())
    except URLError:
        return {
            "subscription_type": None,
            "rate_limit_tier": None,
            "raw_profile": None,
        }


def parse_scopes(scope_str: str) -> list[str]:
    """Parse space-separated scopes."""
    return scope_str.split() if scope_str else []


class OAuthService:
    """OAuth 2.0 service with PKCE."""

    def __init__(self):
        self.code_verifier = generate_code_verifier()
        self.auth_code_listener: Optional[AuthCodeListener] = None
        self.manual_auth_resolver: Optional[Callable[[str], None]] = None
        self.port: Optional[int] = None

    async def start_oauth_flow(
        self,
        auth_url_handler: Callable[[str], Any],
        options: Optional[dict] = None,
    ) -> OAuthTokens:
        """Start OAuth flow."""
        opts = options or {}

        self.auth_code_listener = AuthCodeListener()
        self.port = await self._start_listener()

        code_challenge = generate_code_challenge(self.code_verifier)
        state = generate_state()

        manual_url = build_auth_url(code_challenge, state, self.port, is_manual=True, **opts)
        automatic_url = build_auth_url(code_challenge, state, self.port, is_manual=False, **opts)

        authorization_code = await self._wait_for_code(
            state,
            lambda: self._on_ready(manual_url, automatic_url, opts.get("skipBrowserOpen"), auth_url_handler),
        )

        is_automatic = self.auth_code_listener.has_pending_response() if self.auth_code_listener else False

        token_response = exchange_code_for_tokens(
            authorization_code,
            state,
            self.code_verifier,
            self.port,
            not is_automatic,
            opts.get("expiresIn", 86400),
        )

        profile_info = fetch_profile_info(token_response["access_token"])

        if is_automatic and self.auth_code_listener:
            scopes = parse_scopes(token_response.get("scope", ""))
            self.auth_code_listener.handle_success_redirect(scopes)

        return self._format_tokens(token_response, profile_info)

    def _start_listener(self) -> int:
        if self.auth_code_listener:
            return self.auth_code_listener.start()
        return 8888

    def _on_ready(
        self,
        manual_url: str,
        automatic_url: str,
        skip_browser: bool,
        handler: Callable[[str], Any],
    ) -> None:
        if skip_browser:
            handler(manual_url, automatic_url)
        else:
            handler(manual_url)
            webbrowser.open(automatic_url)

    async def _wait_for_code(
        self,
        state: str,
        on_ready: Callable[[], Any],
    ) -> str:
        if not self.auth_code_listener:
            raise RuntimeError("Listener not started")

        self.auth_code_listener.wait_for_authorization(state, on_ready)
        return self.auth_code_listener.auth_code or ""

    def handle_manual_auth_code_input(
        self,
        authorization_code: str,
        state: str,
    ) -> None:
        """Handle manual auth code input."""
        if self.manual_auth_resolver:
            self.manual_auth_resolver(authorization_code)
            self.manual_auth_resolver = None
            if self.auth_code_listener:
                self.auth_code_listener.close()

    def _format_tokens(
        self,
        response: dict[str, Any],
        profile_info: dict[str, Any],
    ) -> OAuthTokens:
        """Format token response."""
        expires_in = response.get("expires_in", 86400)
        return OAuthTokens(
            access_token=response["access_token"],
            refresh_token=response.get("refresh_token", ""),
            expires_at=time.time() + expires_in,
            scopes=parse_scopes(response.get("scope", "")),
            subscription_type=profile_info.get("subscription_type"),
            rate_limit_tier=profile_info.get("rate_limit_tier"),
            profile=profile_info.get("raw_profile"),
            token_account=response.get("account"),
        )

    def cleanup(self) -> None:
        """Clean up resources."""
        if self.auth_code_listener:
            self.auth_code_listener.close()
        self.manual_auth_resolver = None


async def start_oauth(
    on_success: Callable[[str], None],
    on_cancel: Callable[[], None],
    options: Optional[dict] = None,
) -> dict[str, Any]:
    """Start OAuth flow (CLI entry point)."""
    service = OAuthService()

    def handle_url(url: str) -> None:
        print(f"Authorize: {url}")

    try:
        tokens = await service.start_oauth_flow(handle_url, options)
        on_success(tokens.access_token)
        return {
            "status": "success",
            "access_token": tokens.access_token,
            "expires_at": tokens.expires_at,
        }
    except Exception as e:
        on_cancel()
        return {
            "status": "error",
            "error": str(e),
        }
    finally:
        service.cleanup()


__all__ = [
    "OAuthTokens",
    "OAuthService",
    "AuthCodeListener",
    "generate_code_verifier",
    "generate_code_challenge",
    "generate_state",
    "build_auth_url",
    "exchange_code_for_tokens",
    "fetch_profile_info",
    "parse_scopes",
    "start_oauth",
]