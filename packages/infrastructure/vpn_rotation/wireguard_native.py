"""WireGuard native provider - rotates through local WireGuard configs."""

from __future__ import annotations

import logging
import subprocess
import time
from pathlib import Path

from .models import ProviderConfig, ProviderType, VPNEndpoint

logger = logging.getLogger("vpn_rotation.wireguard_native")


class WireGuardNativeProvider:
    """WireGuard native provider using local .conf files.

    Rotates through multiple WireGuard configs to get different exit IPs.
    Uses wg-quick to connect/disconnect.
    """

    def __init__(self):
        self._config: ProviderConfig | None = None
        self._configs_dir: Path = Path.home() / ".wireguard"
        self._cached_endpoints: list[VPNEndpoint] = []
        self._current_index: int = 0
        self._state_file: Path = Path.home() / ".wireguard" / ".wg_rotator_state"
        self._cache_time: float = 0
        self._cache_ttl: float = 60.0  # 1 minute

    @property
    def name(self) -> str:
        return "wireguard_native"

    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.WIREGUARD_NATIVE

    def configure(self, config: ProviderConfig) -> None:
        self._config = config
        if config.host:  # Custom config directory
            self._configs_dir = Path(config.host)
        self._cached_endpoints = []  # Invalidate cache

    def _load_state(self) -> int:
        """Load current rotation index from state file."""
        if self._state_file.exists():
            try:
                return int(self._state_file.read_text().strip())
            except (OSError, ValueError):
                pass
        return 0

    def _save_state(self, index: int) -> None:
        """Save current rotation index to state file."""
        self._state_file.parent.mkdir(parents=True, exist_ok=True)
        self._state_file.write_text(str(index))

    def _get_config_files(self) -> list[Path]:
        """Get all WireGuard config files."""
        if not self._configs_dir.exists():
            return []
        return sorted(self._configs_dir.glob("proton_*.conf"))

    def _config_to_endpoint(self, config_path: Path) -> VPNEndpoint:
        """Parse config file to extract server info."""
        content = config_path.read_text()

        # Extract country/server from filename
        name = config_path.stem  # e.g., "proton_nl_free12"
        parts = name.split("_")
        country = parts[1].upper() if len(parts) > 1 else "XX"

        # Extract endpoint from config
        endpoint_host = ""
        for line in content.split("\n"):
            if line.startswith("Endpoint ="):
                # Format: "Endpoint = 138.199.7.159:51820"
                endpoint = line.split("=")[1].strip().split(":")[0]
                endpoint_host = endpoint
                break

        return VPNEndpoint(
            host=endpoint_host or config_path.stem,
            port=51820,
            provider=self.name,
            provider_type=self.provider_type,
            country=country,
            city=name,
            instance_id=config_path.stem,
        )

    async def list_endpoints(self) -> list[VPNEndpoint]:
        """List available WireGuard configs as endpoints."""
        # Return cached if fresh
        if self._cached_endpoints and (time.time() - self._cache_time) < self._cache_ttl:
            return self._cached_endpoints

        config_files = self._get_config_files()
        self._cached_endpoints = [self._config_to_endpoint(cf) for cf in config_files]
        self._current_index = self._load_state() % max(len(self._cached_endpoints), 1)
        self._cache_time = time.time()

        logger.info(f"WireGuard native: found {len(self._cached_endpoints)} configs")
        return self._cached_endpoints

    def _get_current_config_name(self) -> str | None:
        """Get name of currently connected config."""
        config_files = self._get_config_files()
        if config_files and self._current_index < len(config_files):
            return config_files[self._current_index].stem
        return None

    async def connect(self, endpoint: VPNEndpoint) -> bool:
        """Connect to a specific WireGuard config."""
        if not endpoint.instance_id:
            return False

        config_name = endpoint.instance_id
        config_path = self._configs_dir / f"{config_name}.conf"

        if not config_path.exists():
            logger.error(f"Config not found: {config_path}")
            return False

        # Disconnect current first
        current = self._get_current_config_name()
        if current:
            try:
                subprocess.run(
                    ["sudo", "wg-quick", "down", str(self._configs_dir / f"{current}.conf")],
                    capture_output=True,
                    timeout=10,
                )
            except Exception as e:
                logger.debug(f"Failed to disconnect {current}: {e}")

        # Connect new
        try:
            result = subprocess.run(
                ["sudo", "wg-quick", "up", str(config_path)],
                capture_output=True,
                text=True,
                timeout=15,
            )
            if result.returncode == 0:
                # Update state
                for i, ep in enumerate(self._cached_endpoints):
                    if ep.instance_id == config_name:
                        self._current_index = i
                        self._save_state(i)
                        break
                logger.info(f"Connected to {config_name}")
                return True
            else:
                logger.error(f"Failed to connect: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"Connection error: {e}")
            return False

    async def disconnect(self, endpoint: VPNEndpoint) -> None:
        """Disconnect from a WireGuard config."""
        if not endpoint.instance_id:
            return

        config_path = self._configs_dir / f"{endpoint.instance_id}.conf"
        try:
            subprocess.run(
                ["sudo", "wg-quick", "down", str(config_path)],
                capture_output=True,
                timeout=10,
            )
            logger.info(f"Disconnected {endpoint.instance_id}")
        except Exception as e:
            logger.debug(f"Disconnect error: {e}")

    async def rotate(self) -> VPNEndpoint | None:
        """Rotate to next WireGuard config."""
        endpoints = await self.list_endpoints()
        if not endpoints:
            return None

        # Move to next
        self._current_index = (self._current_index + 1) % len(endpoints)
        self._save_state(self._current_index)

        next_endpoint = endpoints[self._current_index]

        # Actually connect
        success = await self.connect(next_endpoint)
        if success:
            return next_endpoint
        return None

    async def get_current_exit_ip(self) -> str | None:
        """Get exit IP through current WireGuard tunnel."""
        try:
            # Route through wg0 interface
            result = subprocess.run(
                [
                    "curl",
                    "-s",
                    "--max-time",
                    "5",
                    "-x",
                    "socks5://127.0.0.1:1080",
                    "https://api.ipify.org",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.stdout.strip():
                return result.stdout.strip()
        except Exception:
            pass

        # Fallback: direct curl (if tunnel is default route)
        try:
            result = subprocess.run(
                ["curl", "-s", "--max-time", "5", "https://api.ipify.org"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.stdout.strip():
                return result.stdout.strip()
        except Exception:
            pass

        return None

    async def check_health(self, endpoint: VPNEndpoint) -> bool:
        """Check if WireGuard interface is active for this config."""
        if not endpoint.instance_id:
            return False

        try:
            result = subprocess.run(
                ["sudo", "wg", "show"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            # Check if our config is in the wg output
            return endpoint.instance_id in result.stdout or endpoint.host in result.stdout
        except Exception:
            return False


# Singleton instance
_provider: WireGuardNativeProvider | None = None


def get_wireguard_native_provider() -> WireGuardNativeProvider:
    """Get or create WireGuard native provider."""
    global _provider
    if _provider is None:
        _provider = WireGuardNativeProvider()
    return _provider
