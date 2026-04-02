from pathlib import Path

# Paths
# Assuming src/athena/boot/constants.py -> ../../../.. = PROJECT_ROOT
PROJECT_ROOT = Path(__file__).resolve().parents[3]

LOGS_DIR = PROJECT_ROOT.parent / ".context" / "memories" / "session_logs"
SUPABASE_SEARCH_SCRIPT = PROJECT_ROOT / ".agent" / "scripts" / "smart_search.py"
PROTOCOLS_JSON = PROJECT_ROOT / ".agent" / "protocols.json"
CORE_IDENTITY = (
    PROJECT_ROOT / ".framework" / "v8.2-stable" / "modules" / "Core_Identity.md"
)
SAFE_BOOT_SCRIPT = PROJECT_ROOT / "safe_boot.sh"

# Memory Bank (Token Budget)
MEMORY_BANK_DIR = PROJECT_ROOT.parent / ".context" / "memory_bank"
BOOT_FILES = {
    "userContext.md": MEMORY_BANK_DIR / "userContext.md",
    "productContext.md": MEMORY_BANK_DIR / "productContext.md",
    "activeContext.md": MEMORY_BANK_DIR / "activeContext.md",
}

# Configuration
BOOT_TIMEOUT_SECONDS = 90
EXPECTED_CORE_HASH = "8f2e6f9e248951a84aa48e24e9bfd8239f76c6c8bffd44ee7c9cd854861a8820caed733aafa3b333e8851f372c854d4a"

# Colors (centralized)
from athena.core.colors import GREEN, CYAN, YELLOW, RED, BOLD, DIM, RESET
