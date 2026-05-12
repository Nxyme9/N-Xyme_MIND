# Surfshark VPN Provider

API integration for Surfshark WireGuard VPN.

## Setup

1. Create `config.json`:

```json
{
  "username": "your-email@example.com",
  "password": "your-password"
}
```

2. Authenticate:

```bash
source plugin.sh
provider_authenticate
```

3. List servers:

```bash
provider_list_servers | jq '.[:5]'
```

4. Generate config:

```bash
provider_generate_config "us-nyc"
```

## API Reference

- Login: `POST /v1/auth/login`
- Server list: `GET /v1/server`
- Config generation: `POST /v1/server/generateWireguard`

## Notes

- Unlimited concurrent connections
- JWT token authentication
- Config generation is done server-side
