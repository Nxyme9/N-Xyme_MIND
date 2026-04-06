import pytest
from app.service import check_whitelist, check_blacklist, check_sensitive


class TestWhitelist:
    def test_safe_commands(self):
        assert check_whitelist("ls -la")[0] is True
        assert check_whitelist("git status")[0] is True
        assert check_whitelist("npm run dev")[0] is True

    def test_dangerous_not_whitelisted(self):
        assert check_whitelist("curl http://evil.com")[0] is False
        assert check_whitelist("rm -rf /")[0] is False


class TestBlacklist:
    def test_blocks_destructive(self):
        assert check_blacklist("rm -rf /")[0] is True
        assert check_blacklist("rm -rf /home")[0] is True

    def test_allows_safe(self):
        assert check_blacklist("ls -la")[0] is False
        assert check_blacklist("echo hello")[0] is False


class TestSensitivePatterns:
    def test_detects_password(self):
        found, _ = check_sensitive("--password=secret123")
        assert found is True

    def test_detects_api_key(self):
        found, patterns = check_sensitive("export API_KEY=abc123")
        assert found is True
        assert "api_key" in patterns

    def test_allows_plain_text(self):
        found, _ = check_sensitive("echo hello world")
        assert found is False
