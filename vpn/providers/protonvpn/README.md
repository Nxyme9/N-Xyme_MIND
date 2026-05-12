# ProtonVPN Provider

ProtonVPN uses SRP authentication which is complex to implement outside their official apps. This plugin supports two manual modes:

## Mode 1: Pre-downloaded Config Files

1. Download WireGuard configs from https://account.protonvpn.com/downloads
2. Place `.conf` files in `configs/`:

```bash
cp ~/Downloads/*.conf configs/
```

3. Optional: add metadata comments to configs:

```conf
# Country: US
# City: New York
[Interface]
...
```

## Mode 2: protonvpn-wg-confgen CLI

Install from: https://github.com/0x2b3bfa0/protonvpn-wg-confgen

```bash
protonvpn-wg-confgen --server US-NY#1 --output configs/us-ny-1.conf
```

## Usage

```bash
source plugin.sh
provider_authenticate
provider_list_servers
provider_generate_config "us-ny-1"
```

## Notes

- Max 10 connections
- No programmatic API (SRP auth is too complex for shell scripts)
- Config files are not included in this repository — download separately
