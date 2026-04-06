# MEGA MASTERPLAN: ADHD Vibecoding Stack + Jarvis-like PC Control

## TL;DR

> **Goal**: Ultimate frictionless, ADHD-friendly, everything-automated PC workflow
> **Target**: "Just say/type what you want and it happens"
> **Scope**: Terminal stack + Voice control + Music + Social media + Work automation
> **Status**: Reviewed by 6 agents — all issues resolved

---

## PART 1: Terminal Stack (Core)

### Current State
- System: CachyOS on Wayland | Shell: Fish 4.5.0 | Terminal: Kitty 0.46.2
- Installed: tmux, eza, bat, fd, fzf, zoxide, btop, tldr, lazygit, vim, pip, bun, docker
- Missing: starship, git-delta, atuin, yazi, TPM, JetBrains Mono font

### Stack (7 Tools)

| Category | Tool | Why |
|----------|------|-----|
| Terminal | Kitty | Fast, tabs, Wayland-native |
| Shell | Fish | Autocomplete, great defaults |
| Prompt | Starship | Beautiful, minimal prompt |
| History | Atuin | Searchable, replaces fzf Ctrl+R |
| Files | Yazi | Fast, preview, vim keys |
| Git Diffs | git-delta | Syntax-highlighted, side-by-side |
| Session | tmux | Crash-proof (with resurrect) |

---

## PART 2: Jarvis-like PC Control

| Category | How |
|----------|-----|
| Voice Commands | faster-whisper + Fish aliases |
| Clipboard | wl-clipboard + Fish functions |
| Window Management | wtype + Kitty remote control |
| File Operations | yazi + Fish aliases |
| System Control | Volume, brightness via Fish functions |
| Notifications | notify-send |

---

## PART 3: Music Automation

| Tool | Purpose |
|------|---------|
| playerctl | Control media players (play/pause/next/volume) |
| pactl | PulseAudio volume control |

Aliases: play, pause, next, prev, vol

---

## PART 4: Social Media Automation

| Tool | Purpose |
|------|---------|
| toot | Mastodon CLI |
| newsboat | RSS feeds |
| gh | GitHub notifications |

---

## PART 5: Work Automation

| Command | What |
|---------|------|
| issues | List GitHub issues |
| prs | List pull requests |
| deploy | Trigger CI/CD |
| standup | Daily standup report |

---

## Master Commands

```fish
vibe      # Start coding session
recover   # Recover after crash
helpme    # Show all shortcuts
```

---

## Execution Strategy

### Wave 0: Backup (PREREQUISITE)
- Backup fish, tmux, git configs before ANY changes

### Wave 1: Install (3 parallel)
- Task 1: starship, git-delta, ttf-jetbrains-mono
- Task 2: atuin, yazi
- Task 3: TPM, playerctl, wtype

### Wave 2: Configure (4 parallel)
- Task 4: Kitty (Wayland, Nord theme)
- Task 5: Starship (minimal Nord)
- Task 6: Delta (Nord, side-by-side)
- Task 7: Music/playerctl

### Wave 3: Integrate (4 sequential)
- Task 8: Atuin for fish (fix Ctrl+R conflict)
- Task 9: tmux (Nord, TPM, resurrect)
- Task 10: Fish config (ALL integrations)
- Task 11: Voice/work/music/social aliases

### Wave 4: Verify

---

## TODOs

- [ ] 0. Backup existing configs
- [ ] 1. Install starship, git-delta, ttf-jetbrains-mono
- [ ] 2. Install atuin, yazi
- [ ] 3. Install TPM, playerctl, wtype
- [ ] 4. Configure Kitty for Wayland
- [ ] 5. Configure starship prompt
- [ ] 6. Configure delta for git
- [ ] 7. Configure music/playerctl
- [ ] 8. Configure atuin for fish
- [ ] 9. Update tmux config
- [ ] 10. Update fish config
- [ ] 11. Add voice/work/music/social aliases
- [ ] F1-F9. Final verification

---

## Things AVOIDED
- WezTerm on Wayland (broken)
- Config scattering
- Compression loops
- VPN rotation (doesn't work)
- Docker dependency
- Windows paths

Plan saved: .sisyphus/plans/adhd-vibecoding-stack.md
Ready to execute with /start-work
