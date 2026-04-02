"""VPN 429 Monitor — watches OpenCode logs, auto-rotates VPN on 429."""
import time, os, sys, subprocess

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

LOG_DIR = os.path.expanduser("~/.local/share/opencode/log/")
STATE_FILE = "data/vpn-429-state.json"
ROTATE_SCRIPT = "scripts/vpn-rotation-simulator.py"

def find_latest_log():
    """Find the latest OpenCode log file."""
    if not os.path.exists(LOG_DIR):
        return None
    logs = [os.path.join(LOG_DIR, f) for f in os.listdir(LOG_DIR) if f.endswith('.log')]
    return max(logs, key=os.path.getmtime) if logs else None

def check_for_429(log_path):
    """Check log for 429 errors."""
    if not os.path.exists(log_path):
        return []
    
    errors = []
    with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            if '429' in line or 'insufficient_quota' in line or 'rate limit' in line.lower():
                errors.append(line.strip()[:200])
    return errors

def rotate_vpn():
    """Rotate VPN IP."""
    print("Rotating VPN...")
    r = subprocess.run([sys.executable, ROTATE_SCRIPT], capture_output=True, text=True, timeout=60)
    print(f"  Result: {r.stdout[:200]}")

# Main
print("=== VPN 429 Monitor ===")
log_path = find_latest_log()
if not log_path:
    print("No OpenCode log found")
    sys.exit(1)

print(f"Watching: {log_path}")
errors = check_for_429(log_path)

if errors:
    print(f"Found {len(errors)} rate limit errors:")
    for e in errors[:5]:
        print(f"  {e[:100]}")
    rotate_vpn()
else:
    print("No rate limit errors found")
