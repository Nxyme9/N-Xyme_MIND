# Oracle Cloud Provider

Uses SSH SOCKS5 tunnels to Oracle Cloud VMs. No WireGuard — traffic is tunneled via SSH.

## Setup

1. Create `config.json`:

```json
{
  "vms": [
    {
      "name": "us-ashburn",
      "host": "1.2.3.4",
      "user": "opc",
      "key": "/home/user/.ssh/oracle.pem",
      "socks_port": 1080
    }
  ]
}
```

2. Usage:

```bash
source plugin.sh
provider_list_servers
provider_generate_config "us-ashburn"
# SOCKS5 proxy is now running at 127.0.0.1:1080
```

3. Cleanup:

```bash
provider_cleanup
```

## Notes

- Unlimited connections (limited by VM count)
- Uses SSH key authentication (no password)
- SOCKS5 proxy at `127.0.0.1:<socks_port>`
- Tunnels run in background; cleanup kills them
