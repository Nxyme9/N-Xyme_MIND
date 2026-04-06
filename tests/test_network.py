"""Tests for network modules."""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))


class TestVPNRotator:
    def test_import(self):
        from src.infrastructure.network.vpn_rotator import VPNRotator
        assert VPNRotator is not None

    def test_creation(self):
        from src.infrastructure.network.vpn_rotator import VPNRotator
        rotator = VPNRotator()
        assert rotator is not None

    def test_countries(self):
        from src.infrastructure.network.vpn_rotator import VPNRotator
        assert isinstance(VPNRotator.COUNTRIES, list)
        assert len(VPNRotator.COUNTRIES) > 0

    def test_status(self):
        from src.infrastructure.network.vpn_rotator import VPNRotator
        rotator = VPNRotator()
        status = rotator.status()
        assert hasattr(status, "connected")


class TestVPNManager:
    def test_import(self):
        from src.infrastructure.network.vpn_manager import VPNManager
        assert VPNManager is not None

    def test_creation(self):
        from src.infrastructure.network.vpn_manager import VPNManager
        manager = VPNManager()
        assert manager is not None

    def test_get_summary(self):
        from src.infrastructure.network.vpn_manager import VPNManager
        manager = VPNManager()
        summary = manager.get_summary()
        assert isinstance(summary, dict)


class TestSOCKS5Transport:
    def test_import(self):
        from src.infrastructure.network.socks5_transport import SOCKS5Transport
        assert SOCKS5Transport is not None
