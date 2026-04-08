# Fish Shell Prompt Stuck Runbook

## Symptoms
- Fish shell prompt shows "athena" and won't change
- Tab completion stuck or missing
- Aliases not loading
- `fish` starts slowly or hangs

## Diagnosis Steps

### 1. Check current fish config
```bash
cat ~/.config/fish/config.fish | head -30
```

### 2. Check for athena-specific config
```bash
ls -la ~/.config/fish/
grep -r "athena" ~/.config/fish/ 2>/dev/null
```

### 3. Check fish prompt function
```bash
functions fish_prompt
fish_default_mode
```

### 4. Check for stuck background jobs
```bash
jobs
fg
```

## Resolution

### Reset fish prompt to default:
```bash
# Kill any stuck athena processes
pkill -f athena || true

# Revert to default fish prompt
fish_default_key_bindings
fish_config prompt show

# Or manually set prompt
functions -e fish_prompt
```

### Recreate fish config:
```bash
# Backup current config
cp ~/.config/fish/config.fish ~/.config/fish/config.fish.bak

# Create minimal config
cat > ~/.config/fish/config.fish << 'EOF'
# Minimal Fish Config
set -g fish_greeting ""

# Add local bin to path
if test -d "$HOME/.local/bin"
    set -gx PATH $HOME/.local/bin $PATH
end
EOF
```

### Re-source env.sh:
```bash
# In fish shell
source env.sh

# Or restart fish
exec fish
```

### If athena prompt is hardcoded:
```bash
# Check for custom prompt in athena
cat packages/athena-framework/src/shell/prompt.fish 2>/dev/null

# Override with default
echo 'function fish_prompt
    echo "❯ "
end' > ~/.config/fish/functions/fish_prompt.fish
```

## Prevention
- Keep fish config minimal
- Check config on new machine setup
- Use `env.sh` for environment, not fish config
- Test prompt after package updates
