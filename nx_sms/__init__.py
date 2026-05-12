"""
NxSMS - Self-Learning SMS API Key Rotator
=========================================

Multi-key SMS API rotation with circuit breakers and SQLite learning.

Usage:
    from nx_sms import NxSMS
    
    sms = NxSMS()
    result = sms.send("+15551234567", "Hello!")
"""

__version__ = "0.1.0"

from nx_sms.core import NxSMS, SMSResult, CircuitBreaker
from nx_sms.core import init_db, record_outcome, get_key_stats

__all__ = [
    "NxSMS",
    "SMSResult", 
    "CircuitBreaker",
    "init_db",
    "record_outcome",
    "get_key_stats",
]