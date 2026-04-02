# Master Plan: Full CachyOS Industry Gold Standard Audit

## TL;DR

> 12 parallel explore agents auditing every layer of a CachyOS desktop (Ryzen + 30GB DDR5 + NVMe + NVIDIA 3080 Ti). Each agent covers one domain, returns severity-rated findings. Results consolidated into single action list.
>
> **Estimated Effort**: 5-10 minutes (parallel execution)
> **Parallel Execution**: YES - 12 agents simultaneously
> **Output**: Consolidated findings + prioritized fix list

---

## Context

User's CachyOS desktop has accumulated AI-generated configs, conflicting sysctl files, dead services, and misconfigurations. Previous audit found 16 issues (fixed). Need comprehensive gold-standard audit of entire OS stack.

---

## Agent Dispatch Plan

```
Wave 1 (ALL 12 RUN SIMULTANEOUSLY):

Agent 1  → Kernel & Memory
Agent 2  → CPU & Scheduling  
Agent 3  → Disk & Filesystem
Agent 4  → Network & Firewall
Agent 5  → Security & Hardening
Agent 6  → Boot & Services
Agent 7  → GPU & Display
Agent 8  → Audio & Input
Agent 9  → Package Management
Agent 10 → User Environment
Agent 11 → Logging & Monitoring
Agent 12 → Containers & Virtualization

Wave 2 (After all agents complete):
Consolidation → Merge all findings into single action list
```

---

## TODOs

- [ ] 1. Agent 1: Kernel & Memory Audit

  **What to do**:
  - Run `sysctl -a` and check ALL vm.* parameters against gold standard
  - Check zram config: `zramctl`, `/etc/systemd/zram-generator.conf`
  - Check swap usage: `free -h`, `/proc/swaps`
  - Check hugepages: current vs config vs actual usage
  - Check OOM killer config: `/proc/sys/vm/oom_kill_allocating_task`
  - Check memory cgroups: `cat /proc/cgroups`
  - Check NUMA topology: `numactl --hardware`
  - Check transparent hugepages: `/sys/kernel/mm/transparent_hugepage/`

  **QA Scenarios**:
  ```
  Scenario: Kernel params gold standard check
    Tool: Bash
    Steps:
      1. Run sysctl -a, grep all vm.* params
      2. Compare against CachyOS desktop gold standard
      3. Flag any deviation from optimal values
    Expected Result: List of misconfigured vm parameters with correct values
    Evidence: .sisyphus/evidence/audit-1-kernel.txt
  ```

- [ ] 2. Agent 2: CPU & Scheduling Audit

  **What to do**:
  - Check CPU governor: `/sys/devices/system/cpu/cpu*/cpufreq/scaling_governor`
  - Check boost status: `/sys/devices/system/cpu/cpufreq/boost`
  - Check C-states: `/sys/devices/system/cpu/cpu*/cpuidle/`
  - Check scheduler: `/sys/block/*/queue/scheduler`
  - Check AMD-specific: `amd-pstate` driver, CPPC, preferred cores
  - Check IRQ balancing: `systemctl status irqbalance`
  - Check CPU isolation: `isolcpus`, `nohz_full`, `rcu_nocbs`
  - Check thermal: `sensors` output

  **QA Scenarios**:
  ```
  Scenario: CPU performance verification
    Tool: Bash
    Steps:
      1. Check all CPU governors are "performance"
      2. Verify boost is enabled
      3. Check C-states are not too deep
    Expected Result: CPU configured for maximum desktop performance
    Evidence: .sisyphus/evidence/audit-2-cpu.txt
  ```

- [ ] 3. Agent 3: Disk & Filesystem Audit

  **What to do**:
  - Check mount options: `mount | grep "^/dev"` - noatime, discard, compress
  - Check BTRFS subvolumes: `btrfs subvolume list /`
  - Check BTRFS balance: `btrfs balance status /`
  - Check BTRFS scrub: `btrfs scrub status /`
  - Check NVMe health: `sudo smartctl -a /dev/nvme0n1`
  - Check NVMe TRIM: `systemctl status fstrim.timer`
  - Check I/O scheduler per device
  - Check `/etc/fstab` for issues
  - Check tmpfiles.d rules
  - Check disk space: `df -h`

  **QA Scenarios**:
  ```
  Scenario: Filesystem health check
    Tool: Bash
    Steps:
      1. Verify all BTRFS mounts have noatime,compress=zstd,discard=async
      2. Check fstrim.timer is enabled
      3. Verify NVMe health is OK
    Expected Result: Filesystem properly configured for SSD longevity
    Evidence: .sisyphus/evidence/audit-3-disk.txt
  ```

- [ ] 4. Agent 4: Network & Firewall Audit

  **What to do**:
  - Check firewall: `iptables -L -n` or `nft list ruleset` or `ufw status`
  - Check DNS: `resolvectl status`, check for leaks
  - Check NetworkManager: `nmcli connection show`
  - Check open ports: `ss -tlnp`
  - Check TCP tuning: BBR, buffer sizes, fastopen
  - Check MTU: `ip link show`
  - Check WiFi power management: `iwconfig wlan0`
  - Check IPv6: enabled/disabled, privacy extensions
  - Check ARP cache: `ip neigh show`

  **QA Scenarios**:
  ```
  Scenario: Network security baseline
    Tool: Bash
    Steps:
      1. List all listening ports
      2. Check firewall rules
      3. Verify DNS configuration
    Expected Result: Network properly secured, no unexpected ports
    Evidence: .sisyphus/evidence/audit-4-network.txt
  ```

- [ ] 5. Agent 5: Security & Hardening Audit

  **What to do**:
  - Check sudoers: `sudo -l` - NOPASSWD issues
  - Check SSH: `/etc/ssh/sshd_config` and drop-ins
  - Check AppArmor/SELinux: `aa-status` or `getenforce`
  - Check kernel hardening: `kernel.randomize_va_space`, `kernel.kptr_restrict`, `kernel.yama.ptrace_scope`
  - Check file permissions: `/etc/shadow`, `/etc/sudoers`, SSH keys
  - Check user groups: `groups nxyme` - unnecessary privileges
  - Check polkit rules: `/etc/polkit-1/rules.d/`
  - Check PAM: `/etc/pam.d/` for weak configs
  - Check secrets: grep for API keys in config files

  **QA Scenarios**:
  ```
  Scenario: Security baseline verification
    Tool: Bash
    Steps:
      1. Verify no NOPASSWD ALL in sudoers
      2. Check AppArmor is enforcing
      3. Verify kernel hardening params
    Expected Result: System meets security baseline
    Evidence: .sisyphus/evidence/audit-5-security.txt
  ```

- [ ] 6. Agent 6: Boot & Services Audit

  **What to do**:
  - Run `systemd-analyze blame` - find slow services
  - Run `systemd-analyze critical-chain` - boot bottleneck
  - Check failed units: `systemctl list-units --failed`
  - Check user failed: `systemctl --user list-units --failed`
  - Check all enabled services: `systemctl list-unit-files --state=enabled`
  - Check all user services: `systemctl --user list-unit-files --state=enabled`
  - Check service dependencies and ordering
  - Check for dead/unused services that can be disabled

  **QA Scenarios**:
  ```
  Scenario: Boot performance verification
    Tool: Bash
    Steps:
      1. Check boot time is under 15 seconds
      2. Verify no failed units
      3. List services that can be disabled
    Expected Result: Fast clean boot with no failures
    Evidence: .sisyphus/evidence/audit-6-boot.txt
  ```

- [ ] 7. Agent 7: GPU & Display Audit

  **What to do**:
  - Check NVIDIA driver: `nvidia-smi`, driver version, CUDA version
  - Check KMS: `lsmod | grep nvidia_drm`, modeset status
  - Check Wayland/X11: `echo $XDG_SESSION_TYPE`
  - Check display manager: `systemctl status sddm`
  - Check GPU power management: nvidia-powerd, powermizer
  - Check Vulkan: `vulkaninfo --summary`
  - Check OpenGL: `glxinfo | grep "OpenGL renderer"`
  - Check monitor config: `xrandr` or `wlr-randr`
  - Check shader cache: `__GL_SHADER_DISK_CACHE` env vars

  **QA Scenarios**:
  ```
  Scenario: GPU performance verification
    Tool: Bash
    Steps:
      1. Verify NVIDIA driver loaded and working
      2. Check GPU is in performance mode
      3. Verify shader cache is enabled
    Expected Result: GPU properly configured for gaming/compute
    Evidence: .sisyphus/evidence/audit-7-gpu.txt
  ```

- [ ] 8. Agent 8: Audio & Input Audit

  **What to do**:
  - Check PipeWire: `systemctl --user status pipewire pipewire-pulse wireplumber`
  - Check audio devices: `pactl list sinks short`
  - Check audio sample rate: PipeWire config
  - Check keyd: `systemctl status keyd`, config validation
  - Check input devices: `libinput list-devices`
  - Check udev rules for input: `/etc/udev/rules.d/99-input*`
  - Check ydotool: `systemctl --user status ydotool`
  - Check C920 mic: volume levels, default source
  - Check Kanata: `systemctl --user status kanata`

  **QA Scenarios**:
  ```
  Scenario: Audio input verification
    Tool: Bash
    Steps:
      1. Verify PipeWire is running
      2. Check default audio sink/source
      3. Verify keyd remapping works
    Expected Result: Audio and input properly configured
    Evidence: .sisyphus/evidence/audit-8-audio.txt
  ```

- [ ] 9. Agent 9: Package Management Audit

  **What to do**:
  - Check pacman config: `/etc/pacman.conf` - ParallelDownloads, CleanMethod
  - Check pacman cache size
  - Check orphaned packages: `pacman -Qtdq`
  - Check database integrity: `pacman -Dk`
  - Check for partial upgrades: `pacman -Qkk`
  - Check AUR helper: yay/paru config
  - Check pacman hooks: `/etc/pacman.d/hooks/`
  - Check mirrorlist: `/etc/pacman.d/mirrorlist`
  - Check keyring: `pacman-key --list-keys`
  - Check for held/pinned packages

  **QA Scenarios**:
  ```
  Scenario: Package management health
    Tool: Bash
    Steps:
      1. Verify no orphaned packages
      2. Check database integrity
      3. Verify CleanMethod is set
    Expected Result: Package management clean and optimized
    Evidence: .sisyphus/evidence/audit-9-packages.txt
  ```

- [ ] 10. Agent 10: User Environment Audit

  **What to do**:
  - Check shell: `echo $SHELL`, Fish config
  - Check PATH: duplicate entries, ordering
  - Check env vars: `~/.bash_profile`, `~/.profile`, `~/.config/environment.d/`
  - Check dotfiles: `~/.bashrc`, `~/.config/fish/config.fish`
  - Check aliases: duplicates, broken references
  - Check XDG dirs: `~/.config/user-dirs.dirs`
  - Check locale: `localectl status`
  - Check timezone: `timedatectl status`
  - Check editor/visual: `$EDITOR`, `$VISUAL`

  **QA Scenarios**:
  ```
  Scenario: User environment health
    Tool: Bash
    Steps:
      1. Check PATH for duplicates
      2. Verify locale is consistent
      3. Check env vars don't conflict
    Expected Result: Clean user environment, no conflicts
    Evidence: .sisyphus/evidence/audit-10-env.txt
  ```

- [ ] 11. Agent 11: Logging & Monitoring Audit

  **What to do**:
  - Check journald config: `/etc/systemd/journald.conf` - size limits
  - Check journal size: `journalctl --disk-usage`
  - Check log rotation: `logrotate` config
  - Check dmesg for errors: `dmesg -l err,warn`
  - Check kernel ring buffer: `dmesg | grep -i "error\|fail\|bug\|warn"`
  - Check systemd journal for persistent errors
  - Check core dumps: `coredumpctl list`
  - Check audit daemon: `systemctl status auditd`

  **QA Scenarios**:
  ```
  Scenario: Logging health check
    Tool: Bash
    Steps:
      1. Verify journal size is capped
      2. Check for critical errors in dmesg
      3. Verify log rotation is working
    Expected Result: Logging properly configured, no critical errors
    Evidence: .sisyphus/evidence/audit-11-logging.txt
  ```

- [ ] 12. Agent 12: Containers & Virtualization Audit

  **What to do**:
  - Check Docker: `systemctl status docker`, daemon config
  - Check Podman: `podman info`
  - Check libvirt: `systemctl status libvirtd`, VM configs
  - Check QEMU/KVM: `kvm-ok`, `/dev/kvm` permissions
  - Check container storage: `docker system df`
  - Check container networks: `docker network ls`
  - Check cgroups v2: `stat -fc %T /sys/fs/cgroup/`
  - Check namespaces: user namespaces enabled
  - Check seccomp: container runtime defaults

  **QA Scenarios**:
  ```
  Scenario: Virtualization health
    Tool: Bash
    Steps:
      1. Check KVM is available and accessible
      2. Verify no stale containers
      3. Check container storage isn't bloated
    Expected Result: Virtualization properly configured
    Evidence: .sisyphus/evidence/audit-12-virt.txt
  ```

---

## Final Consolidation Wave

- [ ] C1. Merge all 12 agent reports into single prioritized list
- [ ] C2. Present findings to user
- [ ] C3. User decides which fixes to apply

---

## Success Criteria

- All 12 agents complete and return findings
- Every finding has severity rating (Critical/High/Medium/Low)
- Every finding has exact file path or command
- Zero findings require assumptions
- Consolidated list is actionable (fix commands included)
