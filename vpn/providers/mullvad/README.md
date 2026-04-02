# Mullvad VPN Provider

Full API integration for Mullvad WireGuard VPN.

## Setup

1. Create `config.json`:

```json
{
  "account_number": "1234567890"
}
```

2. Authenticate:

```bash
source plugin.sh
provider_authenticate
```

3. List servers:

```bash
provider_list_servers
```

4. Generate config:

```bash
provider_generate_config "se-got-wg-001"
```

## API Reference

- Server list: `GET /public/relays/wireguard/v1/`
- Key registration: `POST /public/relays/wireguard/v1/`
- Auth: Bearer token = account number

## Notes

- Max 5 concurrent connections per account
- DNS server: `10.64.0.1`
- Port: 51820
- Keys are registered per-config — each generate call creates a new keypair
