# Master Recovery Plan — Post-CachyOS Reinstall

## Status Summary

### ✅ RESOLVED (18 issues fixed)

| # | Issue | Fix | Status |
|---|-------|-----|--------|
| 1 | Drives not mounting on reboot | fstab UUID entries + ntfs3/ntfs-3g | ✅ All 5 auto-mount |
| 2 | Node.js missing | `pacman -S nodejs npm` | ✅ v25.8.2 |
| 3 | uv/uvx missing | `pacman -S uv` | ✅ 0.11.2 |
| 4 | Ollama missing | `paru -S ollama` | ✅ Running |
| 5 | sequential-thinking MCP broken | npx npm package | ✅ Working |
| 6 | memory MCP broken | npx npm package | ✅ Working |
| 7 | git MCP broken | uvx mcp-server-git | ✅ Ready |
| 8 | serena MCP broken | uvx serena | ✅ Ready |
| 9 | context7 MCP | Remote SSE | ✅ Working |
| 10 | github MCP | Go binary | ✅ Working |
| 11 | hindsight imports broken | `uv pip reinstall` packages | ✅ Imports OK |
| 12 | opencode.json wrong paths | `nxyme` → `n-xyme` relative | ✅ Fixed |
| 13 | Explore agents wrong model | minimax-m2.5 → mimo-v2-pro-free | ✅ Fixed |
| 14 | Explore agents can't run bash | `bash: deny` → `bash: allow` | ✅ Fixed |
| 15 | opencode hangs on startup | Disabled broken MCPs, fixed context7 | ✅ Starts now |
| 16 | Fish PATH missing opencode | `fish_add_path ~/.opencode/bin` | ✅ Fixed |
| 17 | Can't read /mnt files | `external_directory: allow` | ✅ Fixed |
| 18 | Game ISO mounted | `mount -o loop` to /mnt/game-iso | ✅ Ready |

### ❌ REMAINING (5 issues)

| # | Issue | Why | Fix Needed |
|---|-------|-----|------------|
| 1 | athena MCP disabled | Python 3.14 + broken venv | Find npm alt or fix venv |
| 2 | Ollama no models | Need to pull | `ollama pull qwen2.5:14b` |
| 3 | Game not installed | ISO mounted, needs Wine setup | `wine setup.exe` |
| 4 | Backup image not extracted | .img.zst needs decompression | `zstd -d` → mount → copy |
| 5 | Cache cleanup | uv cache 1.5GB | `uv cache clean` |

---

## Execution Order

### Phase 1: Quick Wins (5 min)
```
1. Pull Ollama model: ollama pull qwen2.5:3b (small, for testing)
2. Clean uv cache: uv cache clean
3. Enable hindsight MCP in .opencode/opencode.json
```

### Phase 2: Game Time (15-30 min)
```
4. Install game: cd /mnt/game-iso && wine setup.exe
5. Play game
```

### Phase 3: Data Recovery (20-40 min)
```
6. Decompress backup image: zstd -d .img.zst -o backup.img
7. Mount: sudo losetup + mount
8. Copy nx_openmore: cp -r /mnt/backup-root/home/nxyme/nx_openmore /mnt/Library/
9. Unmount + cleanup
```

### Phase 4: Fix athena MCP (when ready)
```
10. Option A: Find npm alternative for athena
11. Option B: Rebuild Python venv with uv for Python 3.14
12. Option C: Disable permanently if not needed
```

---

## Verification Commands

```bash
# Drives
df -h | grep /mnt

# MCPs
opencode debug config

# Ollama
ollama list

# Game
ls /mnt/game-iso/setup.exe

# Backup
ls /mnt/NxymeImages/backup.img 2>/dev/null || echo "not decompressed yet"
```

---

## Files Changed This Session

- `/etc/fstab` — 5 drive mount entries
- `/etc/sudoers.d/nxyme-mount` — passwordless mount
- `.opencode/opencode.json` — MCP commands, permissions
- `config/opencode.json` — paths fixed
- `config/oh-my-opencode.json` — agent models fixed
- `~/.config/fish/config.fish` — opencode PATH
- `bin/mount-backup.sh` — backup mount script
- `bin/mount-image.sh` — generic image mounter
