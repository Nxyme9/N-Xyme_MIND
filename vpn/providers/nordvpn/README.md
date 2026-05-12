# NordVPN Provider

Full API integration for NordVPN WireGuard.

## Setup

1. Create `config.json`:

```json
{
  "username": "your-nordvpn-email",
  "password": "your-nordvpn-password"
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
provider_generate_config "us8000"
```

## API Reference

- Auth token: `POST /v1/users/tokens`
- Server list: `GET /v1/servers?limit=0`
- Credentials: `GET /v1/users/services/credentials`

## Notes

- Max 10 concurrent connections
- DNS: `103.86.96.100, 103.86.99.100`
- Port: 51820
- Only WireGuard-UDP servers are returned
