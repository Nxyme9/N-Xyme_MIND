# Secret Rotation Guide

This document covers rotating API keys in the N-Xyme_MIND workspace.

## Architecture

| Location | File | Keys |
|----------|------|------|
| Global | `~/.config/opencode/.env` | OPENCODE_API_KEY, OPENROUTER_API_KEY, GOOGLE_API_KEY |
| Project | `~/N-Xyme_CODE/N-Xyme_MIND/.env` | GITHUB_PERSONAL_ACCESS_TOKEN, JARVIS_API_KEY |

Both files should have `600` permissions (`chmod 600 .env`).

## Rotation Schedule

- **Standard**: Every 90 days
- **After team change**: Immediate
- **If compromised**: Emergency rotation (see below)

---

## Key Rotation Procedures

### 1. OPENCODE_API_KEY

**Where to get new key:**
1. Go to https://opencode.ai/settings
2. Navigate to API Keys section
3. Generate new key

**How to rotate:**
```bash
# Backup current key (optional)
cp ~/.config/opencode/.env ~/.config/opencode/.env.backup

# Edit global .env
nano ~/.config/opencode/.env
# Update: OPENCODE_API_KEY=<new_key>
```

**Verify:**
```bash
opencode --version  # Should work without errors
```

---

### 2. OPENROUTER_API_KEY

**Where to get new key:**
1. Go to https://openrouter.ai/keys
2. Generate new key

**How to rotate:**
```bash
nano ~/.config/opencode/.env
# Update: OPENROUTER_API_KEY=<new_key>
```

**Verify:**
```bash
# Test with a simple API call or check dashboard
```

---

### 3. GOOGLE_API_KEY

**Where to get new key:**
1. Go to https://console.cloud.google.com/apis/credentials
2. Select or create API key
3. Restrict to needed APIs (recommended)

**How to rotate:**
```bash
nano ~/.config/opencode/.env
# Update: GOOGLE_API_KEY=<new_key>
```

**Verify:**
```bash
# Test with a simple API call
```

---

### 4. GITHUB_PERSONAL_ACCESS_TOKEN

**Where to get new key:**
1. Go to https://github.com/settings/tokens
2. Generate new token (classic)
3. Select scopes: `repo`, `workflow`, `read:org`

**How to rotate:**
```bash
# Backup
cp ~/N-Xyme_CODE/N-Xyme_MIND/.env ~/N-Xyme_CODE/N-Xyme_MIND/.env.backup

# Edit
nano ~/N-Xyme_CODE/N-Xyme_MIND/.env
# Update: GITHUB_PERSONAL_ACCESS_TOKEN=<new_token>
```

**Verify:**
```bash
gh auth status
# Or: gh api user
```

---

### 5. JARVIS_API_KEY

**Where to get new key:**
1. Check project documentation or ask team lead
2. Generate via Jarvis dashboard if available

**How to rotate:**
```bash
nano ~/N-Xyme_CODE/N-Xyme_MIND/.env
# Add/Update: JARVIS_API_KEY=<new_key>
```

**Verify:**
```bash
# Test via project health check or API call
```

---

## Rollback Procedure

If rotation fails:

```bash
# Restore from backup
cp ~/.config/opencode/.env.backup ~/.config/opencode/.env
# Or
cp ~/N-Xyme_CODE/N-Xyme_MIND/.env.backup ~/N-Xyme_CODE/N-Xyme_MIND/.env

# Verify restore
cat ~/.config/opencode/.env | grep API_KEY
```

---

## Emergency Rotation (Compromised Key)

If you suspect a key is compromised:

1. **Revoke immediately** via the service dashboard
2. **Generate new key** following procedures above
3. **Update .env files** immediately
4. **Verify** the new key works
5. **Check audit logs** for unauthorized usage (service dashboard)
6. **Rotate related keys** if cross-compromise possible

```bash
# Quick emergency rotation script
nano ~/.config/opencode/.env  # Update compromised key
nano ~/N-Xyme_CODE/N-Xyme_MIND/.env
```

---

## Pre-commit Hook

Gitleaks is installed to prevent secret leaks:

```bash
# It runs automatically on commit
# To test manually:
gitleaks detect --source . --report-format json
```

---

## Security Notes

- Never commit `.env` files
- Never share keys in chat or documentation
- Use `.env.example` for templates (no real values)
- Rotate on schedule — don't wait for incidents
