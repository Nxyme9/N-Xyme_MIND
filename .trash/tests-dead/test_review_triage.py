"""Tests for review_triage.py."""

import pytest
from src.intelligence.review_triage import triage_review, ReviewTriage


class TestTriageReview:
    def test_no_sensitive_paths(self):
        result = triage_review("fix typo in config")
        assert result["override"] is False
        assert result["force_oracle"] is False
        assert result["level"] == 0

    def test_auth_keyword(self):
        result = triage_review("fix auth middleware")
        assert result["override"] is True
        assert result["force_oracle"] is True
        assert result["level"] == 3

    def test_security_keyword(self):
        result = triage_review("update security settings")
        assert result["override"] is True

    def test_crypto_keyword(self):
        result = triage_review("implement crypto module")
        assert result["override"] is True

    def test_password_keyword(self):
        result = triage_review("reset password flow")
        assert result["override"] is True

    def test_payment_keyword(self):
        result = triage_review("add payment processing")
        assert result["override"] is True

    def test_sensitive_path_in_list(self):
        result = triage_review("update config", file_paths=["src/auth/middleware.py"])
        assert result["override"] is True

    def test_sensitive_path_api_key(self):
        result = triage_review("update config", file_paths=["src/config/api_key.py"])
        assert result["override"] is True

    def test_sensitive_path_private_key(self):
        result = triage_review("update config", file_paths=["keys/private_key.pem"])
        assert result["override"] is True

    def test_multiple_reasons(self):
        result = triage_review(
            "fix auth and security issues", file_paths=["src/crypto/encrypt.py"]
        )
        assert len(result["reason"].split(",")) >= 2

    def test_no_match_in_task(self):
        result = triage_review("add new button to dashboard")
        assert result["override"] is False

    def test_case_insensitive(self):
        result = triage_review("Fix AUTH Middleware")
        assert result["override"] is True

    def test_word_boundary_no_false_positive(self):
        result = triage_review("authorize user access")
        assert result["override"] is False

    def test_empty_file_paths(self):
        result = triage_review("fix auth", file_paths=[])
        assert result["override"] is True

    def test_none_file_paths(self):
        result = triage_review("fix auth", file_paths=None)
        assert result["override"] is True


class TestReviewTriageClass:
    def test_triage_static(self):
        result = ReviewTriage.triage("fix typo")
        assert result["override"] is False

    def test_triage_with_paths(self):
        result = ReviewTriage.triage("update config", file_paths=["src/auth/login.py"])
        assert result["override"] is True
