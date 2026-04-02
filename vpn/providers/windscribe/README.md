# Windscribe Provider

Manual config files. Generate configs from the Windscribe app or website.

## Setup

1. Generate WireGuard configs from Windscribe (Settings → WireGuard)
2. Place `.conf` files in `configs/`:

```bash
cp *.conf configs/
```

## Usage

```bash
source plugin.sh
provider_list_servers
provider_generate_config "windscribe-us-east"
```

## Notes

- Manual configs only — no API integration
- Unlimited connections
