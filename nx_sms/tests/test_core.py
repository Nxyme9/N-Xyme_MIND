import pytest
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root.parent))


class TestCircuitBreaker:
    def test_closed_allows_requests(self):
        from nx_sms.core import CircuitBreaker
        cb = CircuitBreaker()
        assert cb.should_allow() is True

    def test_open_blocks_until_timeout(self):
        from nx_sms.core import CircuitBreaker, CIRCUIT_BREAKER_THRESHOLD, CIRCUIT_BREAKER_TIMEOUT
        import time
        cb = CircuitBreaker(failures=CIRCUIT_BREAKER_THRESHOLD, state="open", opened_at=time.time())
        assert cb.should_allow() is False

    def test_half_open_after_timeout(self):
        from nx_sms.core import CircuitBreaker, CIRCUIT_BREAKER_THRESHOLD, CIRCUIT_BREAKER_TIMEOUT
        import time
        cb = CircuitBreaker(failures=CIRCUIT_BREAKER_THRESHOLD, state="open", opened_at=time.time() - CIRCUIT_BREAKER_TIMEOUT - 1)
        assert cb.should_allow() is True

    def test_record_success_closes(self):
        from nx_sms.core import CircuitBreaker
        cb = CircuitBreaker(state="open", failures=5)
        cb.record_success()
        assert cb.state == "closed"
        assert cb.failures == 0


class TestNxSMSInputValidation:
    def test_send_empty_phone_returns_error(self):
        from nx_sms.core import NxSMS
        sms = NxSMS()
        result = sms.send("", "Hello")
        assert result.success is False
        assert "required" in result.error.lower()

    def test_send_whitespace_phone_returns_error(self):
        from nx_sms.core import NxSMS
        sms = NxSMS()
        result = sms.send("   ", "Hello")
        assert result.success is False
        assert "required" in result.error.lower()

    def test_send_empty_message_returns_error(self):
        from nx_sms.core import NxSMS
        sms = NxSMS()
        result = sms.send("+15551234567", "")
        assert result.success is False
        assert "required" in result.error.lower()

    def test_send_whitespace_message_returns_error(self):
        from nx_sms.core import NxSMS
        sms = NxSMS()
        result = sms.send("+15551234567", "   ")
        assert result.success is False
        assert "required" in result.error.lower()

    def test_get_available_keys_returns_list(self):
        from nx_sms.core import NxSMS
        sms = NxSMS()
        available = sms.get_available_keys()
        assert isinstance(available, list)


class TestSMSResult:
    def test_dataclass_fields(self):
        from nx_sms.core import SMSResult
        result = SMSResult(success=True, service="test", message="hi")
        assert result.success is True
        assert result.service == "test"
        assert result.message == "hi"


class TestIntegration:
    def test_import_works(self):
        from nx_sms import NxSMS, SMSResult, CircuitBreaker
        assert NxSMS is not None
        assert SMSResult is not None
        assert CircuitBreaker is not None

    def test_has_all_exports(self):
        from nx_sms import __all__
        assert "NxSMS" in __all__
        assert "SMSResult" in __all__
        assert "CircuitBreaker" in __all__
