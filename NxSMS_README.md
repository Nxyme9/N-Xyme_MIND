# NxSMS Rotator

Self-Learning SMS API Key Rotator with automatic failover.

## Features

- **Multi-key rotation** - Automatically rotates through multiple SMS API keys
- **Circuit breakers** - Prevents hammering failed/ quota-exhausted keys
- **SQLite learning** - Tracks success rates per key over time
- **Auto-failover** - Tries next key when one fails
- **7 SMS services** - textbelt, seasms, wifitext, smsmode, smsto, textlocal

## Installation

```bash
# Dependencies already in project
pip install requests  # if needed
```

## Quick Start

```bash
# Send SMS (auto-rotates keys)
python3 sms_rotator.py send +15551234567 "Hello world!"

# Add API key for a service
python3 sms_rotator.py add-key smsto YOUR_API_KEY

# List keys and status
python3 sms_rotator.py list

# Show stats
python3 sms_rotator.py stats

# Health check
python3 sms_rotator.py health
```

## Available Services

| Service | Free Limit | Notes |
|---------|-----------|-------|
| textbelt | 1/day | Default free key (may be blocked in some countries) |
| seasms | 100/new account | Sign up at api.seasms.com |
| wifitext | Daily reload | Sign up at api.wifitext.com |
| smsmode | 20/new account | Sign up at api.smsmode.com |
| smsto | 10/new account | Sign up at smsto.com |
| textlocal | 10/new account | Sign up at textlocal.in |

## Configuration

Keys are stored in: `nx_sms/configs/nx_sms/keys.json`
Learning database: `nx_sms/configs/nx_sms/nx_sms_learning.db`

## Files

- `sms_rotator.py` - CLI interface
- `nx_sms/core/__init__.py` - Core NxSMS library
- `sms-rotator/SPEC.md` - Specification