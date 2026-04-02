# AzireVPN Provider

Manual config files. Download from https://www.azirevpn.com/cfg/wireguard.

## Setup

1. Download WireGuard configs from AzireVPN dashboard
2. Place `.conf` files in `configs/`:

```bash
cp *.conf configs/
```

## Usage

```bash
source plugin.sh
provider_list_servers
provider_generate_config "azire-us-nyc"
```

## Notes

- Manual configs only — no API integration
- AzireVPN supports WireGuard natively
