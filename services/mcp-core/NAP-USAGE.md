# How to safely change the NAP protocol:

## 1. Propose Change
Edit services/mcp-core/nap-protocol.json with your changes

## 2. Validate Change
python3 services/mcp-core/nap-validator.py services/mcp-core/nap-protocol.json

## 3. If Valid, Deploy
- Update all agent tools.json files
- Update MCP server tool definitions
- Update Mojo router source
- Rebuild Mojo binary (if available)

## 4. Monitor
- Watch for errors in MCP server logs
- Check agent functionality
- Rollback if needed

## Approval Rules:
- Major changes (breaking): User approval required
- Minor changes (additive): Agent Builder can approve
- Patch changes (fixes): Auto-approved
