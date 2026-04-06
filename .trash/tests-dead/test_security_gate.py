"""Tests for security_gate.py."""

import pytest
from src.intelligence.security_gate import check_security, SecurityGate


class TestCheckSecurity:
    def test_empty_task_passes(self):
        passed, msg = check_security("")
        assert passed is True
        assert "Empty task" in msg

    def test_auth_blocked(self):
        passed, msg = check_security("implement auth middleware")
        assert passed is False
        assert "BLOCK" in msg
        assert "auth" in msg

    def test_crypto_blocked(self):
        passed, msg = check_security("add crypto module")
        assert passed is False

    def test_password_blocked(self):
        passed, msg = check_security("reset password flow")
        assert passed is False

    def test_encrypt_blocked(self):
        passed, msg = check_security("encrypt user data")
        assert passed is False

    def test_decrypt_blocked(self):
        passed, msg = check_security("decrypt payload")
        assert passed is False

    def test_secret_blocked(self):
        passed, msg = check_security("manage secret config")
        assert passed is False

    def test_credential_blocked(self):
        passed, msg = check_security("store user credential data")
        assert passed is False

    def test_payment_blocked(self):
        passed, msg = check_security("add payment processing")
        assert passed is False

    def test_billing_blocked(self):
        passed, msg = check_security("update billing system")
        assert passed is False

    def test_private_key_blocked(self):
        passed, msg = check_security("generate private.key")
        assert passed is False

    def test_ssl_warn(self):
        passed, msg = check_security("configure ssl certificate")
        assert passed is True
        assert "WARN" in msg

    def test_jwt_warn(self):
        passed, msg = check_security("implement jwt validation")
        assert passed is True
        assert "WARN" in msg

    def test_token_warn(self):
        passed, msg = check_security("refresh access token")
        assert passed is True
        assert "WARN" in msg

    def test_oauth_warn(self):
        passed, msg = check_security("add oauth login")
        assert passed is True
        assert "WARN" in msg

    def test_api_key_warn(self):
        passed, msg = check_security("rotate api.key")
        assert passed is True
        assert "WARN" in msg

    def test_no_security_pass(self):
        passed, msg = check_security("add new button to dashboard")
        assert passed is True
        assert "No security-sensitive" in msg

    def test_case_insensitive(self):
        passed, msg = check_security("implement AUTH middleware")
        assert passed is False


class TestSecurityGateClass:
    def test_check_static(self):
        passed, msg = SecurityGate.check("fix typo")
        assert passed is True

    def test_check_block(self):
        passed, msg = SecurityGate.check("fix auth bug")
        assert passed is False
