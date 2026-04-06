# Secret Leak Response Runbook

## Symptoms
- Gate 5 (secret scan) fails in CI
- Gitleaks detects exposed credentials
- GitHub security alert received

## Immediate Actions (within 5 minutes)

### 1. Identify the leaked secret
```bash
bash bin/quality-gates/gate-5-secrets.sh
```

### 2. Determine secret type
- GitHub PAT (`ghp_*`) → GitHub token
- OpenRouter key (`sk-or-v1-*`) → OpenRouter API key
- OpenCode key (`sk-*`) → OpenCode API key
- Google API key (`AIzaSy*`) → Google API key
- AWS key (`AKIA*`) → AWS access key

### 3. Rotate the compromised credential IMMEDIATELY
- **GitHub PAT**: GitHub Settings → Developer settings → Personal access tokens → Delete → Create new
- **OpenRouter**: OpenRouter dashboard → API Keys → Revoke → Create new
- **Google Cloud**: Google Cloud Console → APIs & Services → Credentials → Delete → Create new
- **AWS**: AWS IAM → Users → Security credentials → Delete access key → Create new

### 4. Update .env file
```bash
# Update the compromised key
nano .env
# Verify it's not in git
git status
```

## Remediation (within 1 hour)

### 5. Check git history for exposure
```bash
git log --all --full-history -- "**/*.env" "**/*.json" "**/*.py"
git log -p --all -S "ghp_" -- "*.json" "*.py" "*.md"
```

### 6. If secret was committed to git:
```bash
# Remove from history (DANGEROUS - rewrites history)
git filter-branch --force --index-filter \
  'git rm --cached --ignore-unmatch .env' \
  --prune-empty --tag-name-filter cat -- --all

# Force push (requires coordination)
git push origin --force --all
```

### 7. Update gitleaks config if needed
```bash
# Add new patterns to .gitleaks.toml if not already covered
cat .gitleaks.toml
```

## Prevention
- [ ] Verify `.env` is in `.gitignore`
- [ ] Run pre-commit hooks: `pre-commit install`
- [ ] Enable GitHub secret scanning on repository
- [ ] Use environment variables, not hardcoded keys
- [ ] Regular credential rotation schedule
