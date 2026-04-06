"""Unit tests for security.mcp_credential_proxy."""

import pytest
from src.security.mcp_credential_proxy import (
    CredentialSource,
    InjectionMode,
    AuditAction,
    CredentialSpec,
    AuditEntry,
)


class TestCredentialSource:
    def test_credential_source_values(self):
        assert CredentialSource.KEYRING.value == "keyring"
        assert CredentialSource.ONEPASSWORD.value == "1password"
        assert CredentialSource.ENVIRONMENT.value == "environment"
        assert CredentialSource.ENCRYPTED_CONFIG.value == "encrypted_config"
        assert CredentialSource.PLAINTEXT_CONFIG.value == "plaintext_config"


class TestInjectionMode:
    def test_injection_mode_values(self):
        assert InjectionMode.PROXY.value == "proxy"
        assert InjectionMode.ENV.value == "env"


class TestAuditAction:
    def test_audit_action_values(self):
        assert AuditAction.CREDENTIAL_ACCESSED.value == "credential_accessed"
        assert AuditAction.CREDENTIAL_NOT_FOUND.value == "credential_not_found"
        assert AuditAction.CREDENTIAL_INJECTED.value == "credential_injected"
        assert AuditAction.PROXY_STARTED.value == "proxy_started"
        assert AuditAction.PROXY_STOPPED.value == "proxy_stopped"


class TestCredentialSpec:
    def test_credential_spec_creation(self):
        spec = CredentialSpec(
            env_var="OPENAI_API_KEY",
            source=CredentialSource.ENVIRONMENT,
            location="MY_KEY",
        )
        assert spec.env_var == "OPENAI_API_KEY"
        assert spec.source == CredentialSource.ENVIRONMENT
        assert spec.location == "MY_KEY"
        assert spec.required is True

    def test_credential_spec_defaults(self):
        spec = CredentialSpec(
            env_var="TEST_KEY", source=CredentialSource.ENVIRONMENT, location="test"
        )
        assert spec.required is True
        assert spec.mask_pattern == "***"


class TestAuditEntry:
    def test_audit_entry_creation(self):
        entry = AuditEntry(
            timestamp="2026-04-06T12:00:00",
            action=AuditAction.CREDENTIAL_ACCESSED,
            credential_name="test_key",
            source="environment",
            success=True,
        )
        assert entry.timestamp == "2026-04-06T12:00:00"
        assert entry.action == AuditAction.CREDENTIAL_ACCESSED
        assert entry.success is True

    def test_audit_entry_to_dict(self):
        entry = AuditEntry(
            timestamp="2026-04-06T12:00:00",
            action=AuditAction.CREDENTIAL_ACCESSED,
            credential_name="test_key",
            source="environment",
            success=True,
        )
        d = entry.to_dict()
        assert d["action"] == "credential_accessed"
        assert d["credential_name"] == "test_key"
