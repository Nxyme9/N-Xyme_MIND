"""Unit tests for infrastructure.network.vpn_manager."""

import pytest
from src.infrastructure.network.vpn_manager import (
    TokenBucket,
    Backend,
    VPNManager,
)


class TestTokenBucket:
    """Test TokenBucket rate limiter."""

    def test_token_bucket_init(self):
        """Test TokenBucket initialization."""
        bucket = TokenBucket("test")
        assert bucket.name == "test"
        assert bucket.rate == 80
        assert bucket.burst == 20

    def test_token_bucket_consume(self):
        """Test token consumption."""
        bucket = TokenBucket("test", rate_per_minute=100, burst_limit=10)
        result = bucket.consume()
        assert result is True

    def test_token_bucket_record_429(self):
        """Test 429 recording."""
        bucket = TokenBucket("test")
        bucket.request_count = 10
        bucket.record_429()
        assert bucket.error_count == 1

    def test_token_bucket_should_switch(self):
        """Test should_switch logic."""
        bucket = TokenBucket("test")
        bucket.request_count = 5
        bucket.observed_quota = 10
        # At 80% of quota (8), with 5 requests, should not switch
        assert bucket.should_switch() is False


class TestBackend:
    """Test Backend class."""

    def test_backend_creation(self):
        """Test Backend initialization."""
        backend = Backend(
            name="test_backend",
            socks_host="localhost",
            socks_port=1080,
        )
        assert backend.name == "test_backend"
        assert backend.socks_host == "localhost"
        assert backend.socks_port == 1080

    def test_backend_default_provider(self):
        """Test Backend default provider."""
        backend = Backend(name="test", socks_host="localhost", socks_port=1080)
        assert backend.provider == "manual"

    def test_backend_is_rate_limited_property(self):
        """Test is_rate_limited property."""
        backend = Backend(name="test", socks_host="localhost", socks_port=1080)
        # Default is not rate limited
        assert backend.is_rate_limited is False


class TestVPNManager:
    """Test VPNManager class."""

    @pytest.fixture
    def vpn_manager(self):
        """Create a VPNManager instance."""
        return VPNManager()

    def test_vpn_manager_init(self, vpn_manager):
        """Test VPNManager initialization."""
        assert vpn_manager is not None

    def test_vpn_manager_has_backends(self, vpn_manager):
        """Test VPNManager has backends list."""
        # VPNManager stores backends as a list, loaded via initialize()
        assert hasattr(vpn_manager, "backends")
        assert isinstance(vpn_manager.backends, list)

    def test_vpn_manager_has_token_buckets(self, vpn_manager):
        """Test VPNManager backends have token buckets."""
        # Each Backend has its own TokenBucket via the 'bucket' attribute
        # Add a mock backend to test
        backend = Backend(name="test", socks_host="localhost", socks_port=1080)
        assert hasattr(backend, "bucket")
        assert isinstance(backend.bucket, TokenBucket)


class TestVPNManagerImports:
    """Test module imports."""

    def test_import_vpn_manager(self):
        """Test VPNManager can be imported."""
        from src.infrastructure.network.vpn_manager import VPNManager

        assert VPNManager is not None

    def test_import_token_bucket(self):
        """Test TokenBucket can be imported."""
        from src.infrastructure.network.vpn_manager import TokenBucket

        assert TokenBucket is not None

    def test_import_backend(self):
        """Test Backend can be imported."""
        from src.infrastructure.network.vpn_manager import Backend

        assert Backend is not None
