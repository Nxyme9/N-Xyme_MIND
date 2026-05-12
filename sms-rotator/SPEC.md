# SMS Rotator App Specification

## Project Overview

- **Name:** SMS Rotator
- **Type:** CLI Application with key rotation
- **Core Functionality:** Send SMS to phone numbers using multiple free-tier API keys with automatic rotation
- **Target Users:** Developers needing free SMS alerts

## Free SMS Sources (2026)

| Service | Free Limit | Key Name |
|---------|-----------|---------|
| TextBelt | 1/day | `textbelt` (shared) |
| SeaSMS | 100/new account | API key after signup |
| Vaval (SMSCMD) | 100/month | API key after signup |
| WiFi Text | Daily reload | API key after signup |
| SMS.to | 10/new account | API key after signup |
| TextLocal | 10/new account | API key after signup |

## Functionality Specification

### Core Features

1. **Multi-key Registration**
   - Add/remove API keys
   - Store keys in JSON config
   - Track usage per key

2. **Key Rotation**
   - Round-robin rotation
   - Skip exhausted keys
   - Track quota remaining

3. **Send SMS**
   - Send to phone number
   - Custom message
   - Auto-select working key

4. **CLI Interface**
   - `sms-rotator send <number> <message>`
   - `sms-rotator add-key <service> <key>`
   - `sms-rotator list-keys`
   - `sms-rotator status`

### User Commands

```bash
# Send SMS
./sms-rotator.py send +15551234567 "Alert: Server down"

# Add key
./sms-rotator.py add-key textbelt my_key_here

# List keys
./sms-rotator.py list-keys

# Status
./sms-rotator.py status
```

## Acceptance Criteria

- [ ] Can add multiple API keys
- [ ] Can send SMS with automatic key selection
- [ ] Handles quota exhausted gracefully
- [ ] Works on CachyOS/Arch Linux
- [ ] CLI is user-friendly