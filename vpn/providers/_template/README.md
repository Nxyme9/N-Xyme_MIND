# Provider Plugin Template

This is the template for creating VPN provider plugins.

## Interface

Every plugin must implement these shell functions:

| Function | Required | Description |
|----------|----------|-------------|
| `provider_info()` | Yes | Returns JSON metadata |
| `provider_authenticate()` | Yes | Auth with provider |
| `provider_list_servers()` | Yes | Returns JSON array of servers |
| `provider_generate_config(server_id)` | Yes | Generates WireGuard config |
| `provider_health_check()` | Yes | Returns 0 if healthy |
| `provider_cleanup()` | Optional | Cleanup on shutdown |

## Creating a New Provider

1. Copy this directory: `cp -r _template/ myprovider/`
2. Edit `myprovider/plugin.sh` — implement all required functions
3. Create `myprovider/config.json` with provider-specific config
4. Add a `myprovider/README.md` with setup instructions

## config.json Format

```json
{
  "api_key": "your-api-key",
  "username": "user",
  "password": "pass"
}
```

## auth_state.json Format

```json
{
  "authenticated": true,
  "token": "...",
  "expires_at": "2026-12-31T23:59:59Z"
}
```

## Server Object Format

```json
{
  "id": "unique-server-id",
  "name": "Server Display Name",
  "country": "US",
  "city": "New York",
  "hostname": "us-ny-01.example.com",
  "port": 51820,
  "load": 42
}
```
