# VPN Rotator — Configuration Guide

> **Last Updated**: 2026-04-03 | **Status**: Ready for Configuration

---

## Quick Start

```bash
# List available VPN configs
python3 vpn/rotator.py --list

# Rotate to next available (manual)
# See Usage section below
```

---

## Supported Providers

| Provider | Auth Type | Config Location | Status |
|----------|-----------|----------------|--------|
| ProtonVPN | WireGuard | `providers/protonvpn/configs/` | Manual download |
| Mullvad | WireGuard | `providers/mullvad/configs/` | Manual download |
| NordVPN | WireGuard | `providers/nordvpn/configs/` | Manual download |
| AzireVPN | WireGuard | `providers/azirevpn/configs/` | Manual download |
| Surfshark | WireGuard | `providers/surfshark/configs/` | Manual download |
| Windscribe | WireGuard | `providers/windscribe/configs/` | Manual download |
| Wireguard | WireGuard | `providers/wireguard/configs/` | Manual |
| Oracle | SOCKS5 | SSH tunnel | Auto (see oracle/) |

---

## Configuration Steps

### 1. ProtonVPN

```bash
# Download from: https://account.protonvpn.com/downloads
# Select: WireGuard configuration files
# Extract to:
cp ~/Downloads/*.conf vpn/providers/protonvpn/configs/
```

### 2. Mullvad

```bash
# Download from: https://mullvad.net/en/account/wireguard-configs
# Extract to:
cp mullvad*.conf vpn/providers/mullvad/configs/
```

### 3. NordVPN

```bash
# Download from: https://my.nordaccount.com/dashboard/integrations/
# Select: WireGuard
# Extract to:
cp *.conf vpn/providers/nordvpn/configs/
```

### 4. Other Providers

Follow README.md in each provider directory for specific instructions.

---

## Usage

### List Available Configs

```bash
python3 vpn/rotator.py --list
```

### Connect Manually

```bash
# ProtonVPN example
cd vpn/providers/protonvpn/configs
sudo wg-quick up us-ca-001.conf

# Disconnect
sudo wg-quick down us-ca-001.conf
```

### Automated Rotation (Future)

The rotator.py is being updated to support automatic discovery and rotation.
For now, configs are available for manual connection.

---

## File Structure

```
vpn/
├── rotator.py              # Main rotation logic
├── opencode-vpn             # CLI wrapper
├── vpnsocks                 # SOCKS5 wrapper
├── providers/
│   ├── protonvpn/
│   │   ├── configs/         # Place WireGuard .conf files here
│   │   ├── plugin.sh        # Provider hooks
│   │   └── README.md
│   ├── mullvad/
│   │   ├── configs/
│   │   └── ...
│   └── oracle/              # Special - SOCKS5 over SSH
│       ├── servers.json
│       └── oracle-vms.json
```

---

## Troubleshooting

### No configs found

```bash
# Verify configs directory has .conf files
ls vpn/providers/protonvpn/configs/
```

### Permission denied

```bash
# WireGuard requires root
sudo python3 vpn/rotator.py --list
```

### Provider not responding

Check provider README.md for service status and alternative configs.

---

## API Keys (Future)

For providers with API access, set environment variables:

```bash
export MULLVAD_API_KEY="your-key"
export NORDVPN_API_KEY="your-key"
```

---

*VPN Rotator v1.0 | N-Xyme_MIND*
