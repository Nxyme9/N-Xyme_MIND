# Drive Mounting Fix — Permanent fstab Entries

## Problem
Drives not auto-mounting on boot after CachyOS reinstall. udisks2 mounts some temporarily but they disappear on reboot.

## Drives Needing Permanent Mount

| Device | UUID | Label | FS | Mount Point |
|--------|------|-------|----|-------------|
| sda2 | `6AD4180DD417D9E1` | Library | ntfs3 | `/mnt/Library` |
| sdb1 | `7E14FDCB14FD8705` | WIN LIBRARY | ntfs3 | `/mnt/WinLibrary` |
| sdc1 | `10A61DBF10A61DBF` | NXYME_CORE | ntfs3 | `/mnt/NxymeCore` |
| sdd3 | `9e0fcc14-83e9-43f7-af74-dc6525b8a473` | NXYME_IMAGES | ext4 | `/mnt/NxymeImages` |
| sde3 | `00248B0A248B01C0` | Backup | ntfs3 | `/mnt/Backup` |

## fstab Lines to Add

**Run `sudo nano /etc/fstab` and paste these at the END:**

```
# === Permanent Drive Mounts (added by recovery) ===

# 5.5TB Library Drive
UUID=6AD4180DD417D9E1  /mnt/Library       ntfs3  defaults,nofail,uid=1000,gid=1000,prealloc  0  0

# 1.8TB Windows Library
UUID=7E14FDCB14FD8705  /mnt/WinLibrary    ntfs3  defaults,nofail,uid=1000,gid=1000,prealloc  0  0

# 894GB NXYME Core
UUID=10A61DBF10A61DBF  /mnt/NxymeCore     ntfs3  defaults,nofail,uid=1000,gid=1000,prealloc  0  0

# 894GB Backup
UUID=00248B0A248B01C0  /mnt/Backup        ntfs3  defaults,nofail,uid=1000,gid=1000,prealloc  0  0

# 894GB NXYME Images (ext4)
UUID=9e0fcc14-83e9-43f7-af74-dc6525b8a473  /mnt/NxymeImages  ext4  defaults,nofail  0  2
```

## Steps

1. Create mount points:
   ```bash
   sudo mkdir -p /mnt/Library /mnt/WinLibrary /mnt/NxymeCore /mnt/Backup /mnt/NxymeImages
   ```

2. Edit fstab:
   ```bash
   sudo nano /etc/fstab
   ```
   Paste the lines above at the END. Save: Ctrl+O, Enter, Ctrl+X.

3. Test without rebooting:
   ```bash
   sudo mount -a
   ```

4. Verify:
   ```bash
   df -h | grep /mnt
   ```

5. Reboot to confirm persistence:
   ```bash
   sudo reboot
   ```

## Options Explained
- `ntfs3` — kernel-native NTFS driver (CachyOS has it, no ntfs-3g needed)
- `nofail` — won't block boot if drive is disconnected
- `uid=1000,gid=1000` — files owned by your user (not root)
- `prealloc` — better performance for large files
- `defaults` — standard mount options
- ext4 `0 2` — fsck priority 2 (after root)

## Troubleshooting
- If `ntfs3` fails, try `ntfs-3g` instead (install with `sudo pacman -S ntfs-3g`)
- If a drive has dirty bit set: `sudo ntfsfix /dev/sdXN`
- Check boot log if mount fails: `journalctl -b | grep mount`
