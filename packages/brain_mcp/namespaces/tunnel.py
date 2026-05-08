"""
Tunnel namespace tools for nx-brain-mcp.

This module contains all tunnel-related MCP tools for the API key rotator.
Functions wrap the key_rotator_v3.py functionality with integrated IP rotation.

IP Rotation features powered by packages/infrastructure/vpn_rotation/:
- Self-learning Q-Learning routing with SQLite
- Multiple provider support (ProtonVPN, SOCKS5, WireProxy)
- Health monitoring with exit IP detection
- Dynamic WireProxy instance spawning
"""

from __future__ import annotations

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


# ============================================================
# API KEY ROTATOR (key_rotator_v3.py)
# ============================================================

# Singleton rotator instance
_rotator = None

# Request queue for managing requests when all keys exhausted
_request_queue: List[Dict[str, Any]] = []
_queue_lock = None

# Fallback mode tracking
_fallback_mode = False
_fallback_reason = ""


# ============================================================
# IP ROTATION (packages/infrastructure/vpn_rotation/)
# ============================================================

_vpn_manager = None
_current_exit_ip = None


def _get_vpn_manager():
    """Lazy-load and initialize the VPN rotation manager."""
    global _vpn_manager
    if _vpn_manager is None:
        try:
            import asyncio
            from packages.infrastructure.vpn_rotation import vpn_rotation_manager

            # Initialize the VPN manager (async)
            try:
                # Try to get or create event loop
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                if loop.is_running():
                    # Schedule initialization for later
                    async def init_vpn():
                        try:
                            await vpn_rotation_manager.initialize()
                        except Exception as e:
                            print(f"[TUNNEL] VPN async init: {e}")

                    asyncio.create_task(init_vpn())
                else:
                    # Run initialization synchronously
                    loop.run_until_complete(vpn_rotation_manager.initialize())
            except Exception as e:
                print(f"[TUNNEL] VPN init warning: {e}")

            _vpn_manager = vpn_rotation_manager
        except Exception as e:
            import logging

            logging.getLogger(__name__).warning(f"Could not load VPN manager: {e}")
            return None
    return _vpn_manager


def _get_current_exit_ip() -> Optional[str]:
    """Get current exit IP using multiple detection services."""
    import requests

    services = [
        "https://api.ipify.org?format=json",
        "https://ifconfig.me/ip",
        "https://icanhazip.com/",
        "https://ipinfo.io/ip",
    ]

    for service in services:
        try:
            resp = requests.get(service, timeout=5)
            if service.endswith("json"):
                return resp.json().get("ip", "")
            else:
                return resp.text.strip()
        except Exception as e:
            logger.debug(f"IP check failed: {e}")
            continue
    return None


def _get_rotator():
    """Lazy-load the rotator to avoid import issues."""
    global _rotator
    if _rotator is None:
        try:
            from scripts.key_rotator_v3 import UltimateKeyRotator

            _rotator = UltimateKeyRotator()
        except Exception as e:
            import logging

            logging.getLogger(__name__).warning(f"Could not load rotator: {e}")
            return None
    return _rotator


def _get_queue_lock():
    """Lazy-init queue lock."""
    global _queue_lock
    if _queue_lock is None:
        import threading

        _queue_lock = threading.Lock()
    return _queue_lock


def tunnel_get_key(provider: str = "openrouter") -> dict[str, Any]:
    """
    Get the current API key for a provider.

    Args:
        provider: Provider name (openrouter, google, groq). Default: openrouter.

    Returns:
        Dict with key details or error.
    """
    try:
        rot = _get_rotator()
        if not rot:
            return {"error": "Rotator not available", "success": False}

        key = rot.get_current_key(provider)
        if key:
            return {
                "success": True,
                "key_id": key.key_id,
                "key": key.key[:12] + "..." if len(key.key) > 12 else key.key,
                "provider": key.provider,
                "request_count": key.request_count,
                "rpm_limit": key.rpm_limit,
                "tpm_limit": key.tpm_limit,
            }
        return {
            "error": f"No keys available for provider: {provider}",
            "success": False,
        }

    except Exception as e:
        return {"error": str(e), "success": False}


def tunnel_get_model() -> dict[str, Any]:
    """
    Get the current model being used.

    Returns:
        Dict with model details or error.
    """
    try:
        rot = _get_rotator()
        if not rot:
            return {"error": "Rotator not available", "success": False}

        model = rot.get_current_model()
        if model:
            return {
                "success": True,
                "model_id": model.model_id,
                "provider": model.provider,
                "context_limit": model.context_limit,
            }
        return {"error": "No models available", "success": False}

    except Exception as e:
        return {"error": str(e), "success": False}


def tunnel_rotate(provider: str = "openrouter") -> dict[str, Any]:
    """
    Rotate to the next API key for a provider.

    Args:
        provider: Provider name. Default: openrouter.

    Returns:
        Dict with new key details or error.
    """
    try:
        rot = _get_rotator()
        if not rot:
            return {"error": "Rotator not available", "success": False}

        key = rot.rotate(provider)
        if key:
            return {
                "success": True,
                "key_id": key.key_id,
                "key": key.key[:12] + "..." if len(key.key) > 12 else key.key,
                "provider": key.provider,
            }
        return {"error": f"Could not rotate for provider: {provider}", "success": False}

    except Exception as e:
        return {"error": str(e), "success": False}


def tunnel_check_error(error: str) -> dict[str, Any]:
    """
    Check if an error indicates rate limit and auto-rotate if needed.

    Args:
        error: Error message to check.

    Returns:
        Dict with rotation result.
    """
    try:
        rot = _get_rotator()
        if not rot:
            return {"error": "Rotator not available", "success": False}

        rotated = rot.check_error_and_rotate(error)
        return {
            "success": True,
            "rotated": rotated,
            "error_checked": error[:100] if error else "",
        }

    except Exception as e:
        return {"error": str(e), "success": False}


def tunnel_health() -> dict[str, Any]:
    """
    Get tunnel health status.

    Returns:
        Dict with health metrics.
    """
    try:
        rot = _get_rotator()
        if not rot:
            return {"error": "Rotator not available", "success": False}

        health = rot.health_check()
        return {
            "success": True,
            "healthy": health.get("healthy", False),
            "keys_available": health.get("keys_available", 0),
            "models_available": health.get("models_available", 0),
            "details": health,
        }

    except Exception as e:
        return {"error": str(e), "success": False}


def tunnel_status() -> dict[str, Any]:
    """
    Get complete tunnel status (both API key and IP rotation).

    Returns:
        Dict with full status information including key, model, and IP.
    """
    try:
        rot = _get_rotator()
        if not rot:
            return {"error": "Rotator not available", "success": False}

        # Get key and model info
        key = rot.get_current_key("openrouter")
        model = rot.get_current_model()
        health = rot.health_check()

        # Get IP info
        ip_info = tunnel_get_current_ip()

        # Get IP health
        ip_health = tunnel_ip_health()

        status = {
            "success": True,
            "current_key": {
                "key_id": key.key_id if key else None,
                "key": key.key[:12] + "..."
                if key and len(key.key) > 12
                else key.key
                if key
                else None,
                "provider": key.provider if key else None,
            }
            if key
            else None,
            "current_model": {
                "model_id": model.model_id if model else None,
                "context_limit": model.context_limit if model else None,
            }
            if model
            else None,
            "current_ip": ip_info.get("current_ip"),
            "ip_health": ip_health.get("healthy", False),
            "health": health,
        }

        return status

    except Exception as e:
        return {"error": str(e), "success": False}


def tunnel_chat(
    messages: List[Dict[str, str]],
    model: str = None,
    provider: str = "openrouter",
    temperature: float = 0.7,
    max_tokens: int = 4096,
    use_fallback: bool = False,  # Disabled by default - no local fallback
) -> dict[str, Any]:
    """
    Make a chat request through the tunnel with auto-rotation.

    Args:
        messages: List of message dicts with 'role' and 'content'.
        model: Model ID (optional, uses current if not specified).
        provider: Provider name. Default: openrouter.
        temperature: Sampling temperature. Default: 0.7.
        max_tokens: Max tokens to generate. Default: 4096.
        use_fallback: Use local LLM fallback if all keys exhausted. Default: False (disabled).

    Returns:
        Dict with response or error.
    """
    # First, try remote API
    try:
        rot = _get_rotator()
        if not rot:
            return {"error": "Rotator not available", "success": False}

        # Get key and make request
        key = rot.get_current_key(provider)
        if not key:
            return {"error": f"No keys available for {provider}", "success": False}

        # Determine model
        if not model:
            model_info = rot.get_current_model()
            model = model_info.model_id if model_info else "openrouter/auto"

        # Build request
        import requests

        headers = {
            "Authorization": f"Bearer {key.key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://n-xyme.github.io",
            "X-Title": "N-Xyme-MIND",
        }

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        # Determine endpoint by provider
        if provider == "openrouter":
            url = "https://openrouter.ai/api/v1/chat/completions"
        elif provider == "google":
            url = "https://generativelanguage.googleapis.com/v1beta/models/chat:generateContent"
        elif provider == "groq":
            url = "https://api.groq.com/openai/v1/chat/completions"
        else:
            return {"error": f"Unknown provider: {provider}", "success": False}

        resp = requests.post(url, headers=headers, json=payload, timeout=120)

        # Check for rate limit
        if resp.status_code == 429:
            # Auto-rotate and retry
            rot.check_error_and_rotate("rate limit 429")
            # Record failure for rate limit
            if rot:
                rot.record_failure()
            return {
                "error": "Rate limited, please retry",
                "success": False,
                "rate_limited": True,
            }

        # Check for other errors that should trigger smart fallback
        if resp.status_code in [401, 402, 403, 500, 502, 503]:
            error_msg = f"API error {resp.status_code}: {resp.text[:200]}"
            if rot:
                rot.record_failure()

            if resp.status_code in [401, 403]:
                if rot:
                    rot.rotate()
                return {
                    "error": error_msg,
                    "success": False,
                    "status_code": resp.status_code,
                    "fallback_tried": False,
                    "recommendation": "Check API key validity",
                }
            elif resp.status_code == 429:
                return {"error": "Rate limited", "success": False, "rate_limited": True}
            elif resp.status_code in [502, 503]:
                if use_fallback:
                    fallback_result = _tunnel_local_chat(
                        messages, temperature, max_tokens, rot
                    )
                    fallback_result["fallback_tried"] = True
                    fallback_result["primary_error"] = error_msg
                    return fallback_result
                return {
                    "error": error_msg,
                    "success": False,
                    "status_code": resp.status_code,
                }
            else:
                if use_fallback:
                    return _tunnel_local_chat(messages, temperature, max_tokens, rot)
                return {
                    "error": error_msg,
                    "success": False,
                    "status_code": resp.status_code,
                }

        if resp.status_code != 200:
            # Record failure for other errors
            if rot:
                rot.record_failure()
            return {
                "error": f"API error: {resp.status_code}",
                "success": False,
                "response": resp.text[:500],
            }

        result = resp.json()

        # Extract response
        if "choices" in result and len(result["choices"]) > 0:
            content = result["choices"][0].get("message", {}).get("content", "")
            # Record successful request
            if rot:
                rot.record_success()
            return {
                "success": True,
                "content": content,
                "model": model,
                "usage": result.get("usage", {}),
                "source": "remote",
            }

        # Record failure for invalid response
        if rot:
            rot.record_failure()
        return {
            "error": "Invalid response format",
            "success": False,
            "response": result,
        }

    except Exception as e:
        error_msg = str(e)
        # Record failure for exception
        if rot:
            rot.record_failure()

    # ============================================================
    # FALLBACK: Try local LLM if remote failed
    # ============================================================
    if use_fallback:
        return _tunnel_local_chat(messages, temperature, max_tokens, rot)

    return {"error": error_msg, "success": False}


def _tunnel_local_chat(
    messages: List[Dict[str, str]],
    temperature: float = 0.7,
    max_tokens: int = 4096,
    local_model: str = "qwen2.5-coder:7b",
    rot=None,
) -> dict[str, Any]:
    """
    Fallback to local Ollama when remote API fails.

    Args:
        local_model: Which Ollama model to use. Default: qwen2.5-coder:7b
                     Options: qwen2.5-coder:7b, llama3.2:3b
        rot: Rotator instance for tracking (optional)
    """
    import requests

    # Try local Ollama (running on port 11434)
    OLLAMA_BASE = "http://localhost:11434"

    payload = {
        "model": local_model,  # Use configured local model
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }

    try:
        resp = requests.post(f"{OLLAMA_BASE}/api/chat", json=payload, timeout=180)

        if resp.status_code == 200:
            result = resp.json()
            content = result.get("message", {}).get("content", "")
            # Record successful fallback
            if rot:
                rot.record_success()
            return {
                "success": True,
                "content": content,
                "model": result.get("model", "local"),
                "usage": result.get("done_count", 0),
                "source": "local_fallback",
            }

        # Record failure for local error
        if rot:
            rot.record_failure()
        return {
            "error": f"Local LLM failed: {resp.status_code}",
            "success": False,
            "response": resp.text[:200] if resp.text else "",
            "source": "local_failed",
        }

    except requests.exceptions.ConnectionError:
        # Record failure for unavailable local
        if rot:
            rot.record_failure()
        return {
            "error": "Local LLM not running (Ollama on port 11434)",
            "success": False,
            "source": "local_unavailable",
        }
    except Exception as e:
        # Record failure for other exceptions
        if rot:
            rot.record_failure()
        return {"error": str(e), "success": False, "source": "local_error"}


def tunnel_stats() -> dict[str, Any]:
    """
    Get tunnel usage statistics.

    Returns:
        Dict with usage stats.
    """
    try:
        rot = _get_rotator()
        if not rot:
            return {"error": "Rotator not available", "success": False}

        # Access state and keys
        state = rot.state
        keys = rot.keys

        # Count keys by provider
        key_counts = {provider: len(key_list) for provider, key_list in keys.items()}

        return {
            "success": True,
            "total_requests": state.total_requests,
            "successful_requests": state.successful_requests,
            "failed_requests": state.failed_requests,
            "rotations": state.total_rotations,
            "current_key_index": state.current_key_index,
            "current_model_index": state.current_model_index,
            "health_score": state.health_score,
            "keys_by_provider": key_counts,
        }

    except Exception as e:
        return {"error": str(e), "success": False}


# ============================================================
# REQUEST QUEUE & FALLBACK MANAGEMENT
# ============================================================


def tunnel_queue_request(
    messages: List[Dict[str, str]],
    model: str = None,
    provider: str = "openrouter",
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> dict[str, Any]:
    """
    Queue a request for processing when keys become available.

    Args:
        messages: List of message dicts with 'role' and 'content'.
        model: Model ID (optional).
        provider: Provider name. Default: openrouter.
        temperature: Sampling temperature. Default: 0.7.
        max_tokens: Max tokens to generate. Default: 4096.

    Returns:
        Dict with queue position or error.
    """
    import uuid

    lock = _get_queue_lock()
    with lock:
        request = {
            "id": str(uuid.uuid4())[:8],
            "messages": messages,
            "model": model,
            "provider": provider,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "queued_at": None,  # Would be datetime.now()
        }
        _request_queue.append(request)
        position = len(_request_queue)

    return {
        "success": True,
        "request_id": request["id"],
        "queue_position": position,
        "queue_size": len(_request_queue),
    }


def tunnel_get_queue_status() -> dict[str, Any]:
    """
    Get status of the request queue.

    Returns:
        Dict with queue status.
    """
    lock = _get_queue_lock()
    with lock:
        return {
            "success": True,
            "queue_size": len(_request_queue),
            "fallback_mode": _fallback_mode,
            "fallback_reason": _fallback_reason,
            "pending_requests": [
                {"id": r["id"], "provider": r["provider"]}
                for r in _request_queue[:10]  # First 10
            ],
        }


def tunnel_set_fallback_mode(enabled: bool, reason: str = "") -> dict[str, Any]:
    """
    Manually enable/disable fallback mode.

    Args:
        enabled: True to enable fallback, False to disable.
        reason: Reason for the change.

    Returns:
        Dict with new fallback status.
    """
    global _fallback_mode, _fallback_reason

    _fallback_mode = enabled
    _fallback_reason = reason

    return {
        "success": True,
        "fallback_mode": _fallback_mode,
        "fallback_reason": _fallback_reason,
    }


def tunnel_process_queue() -> dict[str, Any]:
    """
    Process pending requests in the queue.
    Call this periodically or when keys become available.

    Returns:
        Dict with processing results.
    """
    lock = _get_queue_lock()
    processed = 0
    failed = 0

    with lock:
        original_queue = list(_request_queue)
        _request_queue.clear()

    for req in original_queue:
        result = tunnel_chat(
            messages=req["messages"],
            model=req.get("model"),
            provider=req.get("provider", "openrouter"),
            temperature=req.get("temperature", 0.7),
            max_tokens=req.get("max_tokens", 4096),
            use_fallback=False,  # No fallback in queue processing
        )

        if result.get("success"):
            processed += 1
        else:
            failed += 1
            # Re-queue failed requests
            with lock:
                _request_queue.append(req)

    return {
        "success": True,
        "processed": processed,
        "failed": failed,
        "remaining_queue": len(_request_queue),
    }


# ============================================================
# IP ROTATION FUNCTIONS (integrated from vpn_rotation)
# ============================================================


def tunnel_ip_rotate(provider: str = "socks5") -> dict[str, Any]:
    """
    Rotate to the next IP address (VPN/proxy rotation).

    Uses the self-learning Q-Learning router to select the best IP.

    Args:
        provider: Provider type (socks5, protonvpn, wireproxy). Default: socks5.
                  (Currently not used - uses Q-Learning router for selection)

    Returns:
        Dict with rotation result including new IP.
    """
    global _current_exit_ip

    try:
        vpn = _get_vpn_manager()
        if not vpn:
            # Fallback: no VPN manager, return current IP
            current_ip = _get_current_exit_ip()
            return {
                "success": True,
                "rotated": False,
                "current_ip": current_ip,
                "reason": "VPN manager not available",
            }

        # Get next endpoint via Q-Learning router (no args)
        endpoint = vpn.get_endpoint()
        if endpoint:
            # endpoint is VPNEndpoint dataclass - access attributes directly
            _current_exit_ip = getattr(endpoint, "exit_ip", None) or getattr(
                endpoint, "host", None
            )
            return {
                "success": True,
                "rotated": True,
                "provider": getattr(endpoint, "provider", "unknown"),
                "exit_ip": _current_exit_ip,
                "country": getattr(endpoint, "country", None),
                "port": endpoint.port,
                "host": endpoint.host,
            }

        return {
            "success": False,
            "error": "No endpoints available - VPN manager has no endpoints configured",
        }

    except Exception as e:
        return {"error": str(e), "success": False}


def tunnel_get_current_ip() -> dict[str, Any]:
    """
    Get the current exit IP address.

    Returns:
        Dict with current IP information.
    """
    global _current_exit_ip

    try:
        # Try VPN manager first
        vpn = _get_vpn_manager()
        if vpn:
            endpoint = vpn.get_endpoint()
            if endpoint:
                # endpoint is VPNEndpoint dataclass
                _current_exit_ip = getattr(endpoint, "exit_ip", None) or getattr(
                    endpoint, "host", None
                )

        # Fallback to direct IP check
        if not _current_exit_ip:
            _current_exit_ip = _get_current_exit_ip()

        return {
            "success": True,
            "current_ip": _current_exit_ip,
            "source": "vpn_manager" if vpn else "direct",
        }

    except Exception as e:
        return {"error": str(e), "success": False}


def tunnel_ip_health() -> dict[str, Any]:
    """
    Get health status of IP rotation system.

    Returns:
        Dict with health metrics for all IP endpoints.
    """
    try:
        vpn = _get_vpn_manager()
        if not vpn:
            return {
                "success": True,
                "healthy": False,
                "reason": "VPN manager not available",
                "endpoints": [],
            }

        # Get stats from VPN manager
        stats = vpn.get_stats() if hasattr(vpn, "get_stats") else {}

        return {
            "success": True,
            "healthy": True,
            "stats": stats,
            "endpoints": vpn.get_enabled_nodes()
            if hasattr(vpn, "get_enabled_nodes")
            else [],
        }

    except Exception as e:
        return {"error": str(e), "success": False}


def tunnel_add_socks5_proxy(
    host: str,
    port: int,
    username: Optional[str] = None,
    password: Optional[str] = None,
) -> dict[str, Any]:
    """
    Add a SOCKS5 proxy to the IP rotation pool.

    Args:
        host: Proxy host IP.
        port: Proxy port.
        username: Optional username for auth.
        password: Optional password for auth.

    Returns:
        Dict with addition result.
    """
    try:
        vpn = _get_vpn_manager()
        if not vpn:
            return {"error": "VPN manager not available", "success": False}

        # Add SOCKS5 proxy via VPN manager method
        vpn.add_socks5_proxy(name=host, host=host, port=port)

        return {
            "success": True,
            "added": True,
            "host": host,
            "port": port,
        }

    except Exception as e:
        return {"error": str(e), "success": False}


def tunnel_get_proxy_dict() -> dict[str, Any]:
    """
    Get the current proxy dict for use with requests/httpx.

    Returns:
        Dict with http/https proxy URLs.
    """
    try:
        vpn = _get_vpn_manager()
        if not vpn:
            return {"error": "VPN manager not available", "success": False}

        # Try to get proxy dict from VPN manager
        proxy_dict = vpn.get_proxy_dict() if hasattr(vpn, "get_proxy_dict") else None

        if proxy_dict:
            return {
                "success": True,
                "proxies": proxy_dict,
            }

        # Generate from current endpoint (it's a VPNEndpoint dataclass)
        endpoint = vpn.get_endpoint()
        if endpoint:
            # endpoint is VPNEndpoint dataclass - access attributes directly
            host = getattr(endpoint, "host", None)
            port = getattr(endpoint, "port", None)
            if host and port:
                proxy_url = f"socks5://{host}:{port}"
                return {
                    "success": True,
                    "proxies": {
                        "http": proxy_url,
                        "https": proxy_url,
                    },
                }

        return {
            "success": False,
            "error": "No proxy available",
        }

    except Exception as e:
        return {"error": str(e), "success": False}
