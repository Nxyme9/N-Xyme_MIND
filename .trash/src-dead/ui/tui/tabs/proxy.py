"""Proxy tab - VPN/proxy configuration."""

_safe_json = None


def init(safe_json):
    global _safe_json
    _safe_json = safe_json


def get_content() -> str:
    vpn = _safe_json("configs/vpn/backends.json")
    backends = vpn.get("backends", [])
    content = "PROXY / VPN CONFIGURATION\n\n"
    if backends:
        content += (
            f"{'Name':<15} {'Host':<20} {'Port':<6} {'Provider':<15} {'Country':<10}\n"
        )
        content += "-" * 66 + "\n"
        for b in backends:
            content += f"{b.get('name', '?'):<15} {b.get('socks_host', '?'):<20} {str(b.get('socks_port', '?')):<6} {b.get('provider', '?'):<15} {b.get('country', '?'):<10}\n"
    else:
        content += "  No VPN backends configured"
    return content
