# WireGuard Manual Provider

Generic WireGuard config file provider. Drop `.conf` files into `configs/`.

## Setup

1. Place WireGuard config files in `configs/`:

```bash
cp my-server.conf configs/
```

2. Usage:

```bash
source plugin.sh
provider_list_servers
provider_generate_config "my-server"
```

## Notes

- No API, no authentication
- Unlimited connections
- Works with any WireGuard server (self-hosted, VPS, etc.)
