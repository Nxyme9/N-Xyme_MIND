# Security Policy

## Supported Versions

| Version | Supported | Notes |
|---------|-----------|-------|
| 1.0.x   | ✅        | Current stable |
| < 1.0   | ❌        | Legacy        |

## Reporting Vulnerabilities

### How to Report
1. **DO NOT** create a public GitHub issue
2. Email: security@example.com (replace with your email)
3. Include:
   - Description of vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

### Response Timeline
- Acknowledgment: 24-48 hours
- Initial assessment: 5 days
- Fix timeline: Depends on severity

## Security Measures

### Data Protection
- API keys stored in environment variables only
- No credentials in code or config files
- .env files in .gitignore

### Network Security
- SOCKS5 proxies for IP rotation
- Rate limiting on all endpoints
- Request validation and sanitization

### Code Security
- Pre-commit hooks for secret scanning
- Regular dependency updates
- Input validation on all user inputs

### Local LLM Security
- GGUF models run locally (no cloud data transfer)
- Tool execution sandboxed
- MCP tool permissions controlled

## Security Best Practices

### For Users
1. Never commit `.env` files
2. Use strong API keys
3. Rotate keys regularly
4. Monitor usage for anomalies

### For Contributors
1. Run security gates before PR: `bash bin/quality-gates/gate-5-secrets.sh`
2. Validate all user inputs
3. Use parameterized queries (no string interpolation for SQL)
4. Follow principle of least privilege

## Known Issues

None currently. 

If you discover a security issue, please report it following the process above.

---

Thank you for helping keep N-Xyme MIND secure!