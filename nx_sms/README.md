# NxSMS Rotator

Self-Learning SMS API Key Rotator with automatic failover.

## Structure

```
nx_sms/
├── __init__.py          # Package init
├── core/                # Core library (NxSMS class)
│   └── __init__.py
├── cli/                 # CLI entrypoint
│   └── main.py
├── configs/             # Configuration
│   └── nx_sms/
│       ├── keys.json
│       └── nx_sms_learning.db
└── tests/              # Tests
```

## Usage

```python
# As library
from nx_sms import NxSMS
sms = NxSMS()
sms.send("+15551234567", "Hello!")

# As CLI
python3 -m nx_sms.cli.main send +15551234567 "Hello!"
python3 -m nx_sms.cli.main add-key smsto YOUR_KEY
```

## Services

7 SMS services: textbelt, seasms, wifitext, smsmode, smsto, textlocal

## Installation

```bash
pip install requests
```

## Features

- Multi-key rotation
- Circuit breakers
- SQLite learning
- Auto-failover