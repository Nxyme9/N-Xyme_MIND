"""Config tab - ecosystem config files status."""

from pathlib import Path

CONFIG_FILES = None


def init(config_files):
    global CONFIG_FILES
    CONFIG_FILES = config_files


def get_content() -> str:
    content = "ECOSYSTEM CONFIG FILES\n\n"
    for path, (desc, _) in CONFIG_FILES.items():
        exists = Path(path).exists()
        status = "OK" if exists else "MISSING"
        content += f"  [{status}] {path:<45} {desc}\n"
    content += "\nPress C to edit any config file."
    return content
