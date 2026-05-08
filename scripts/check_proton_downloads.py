#!/usr/bin/env python3
"""
Simple: Check for newly downloaded ProtonVPN configs.
Run this after you've downloaded the files.
"""

from pathlib import Path

OUTPUT_DIR = Path("/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/vpn/providers/protonvpn/configs")
DOWNLOAD_DIR = Path.home() / "Downloads"


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("Checking for downloaded ProtonVPN configs...")
    print("=" * 60)

    # Look for conf files
    patterns = ["*.conf", "*proton*.conf", "*wg*.conf"]

    conf_files = []
    for pattern in patterns:
        conf_files.extend(DOWNLOAD_DIR.glob(pattern))

    if conf_files:
        print(f"\n✓ Found {len(conf_files)} conf files:")
        for f in conf_files:
            print(f"  - {f.name}")
            dest = OUTPUT_DIR / f.name
            import shutil

            shutil.copy2(f, dest)
            print(f"    → Copied to {dest}")

        print(f"\n✅ Done! {len(conf_files)} configs saved to:")
        print(f"   {OUTPUT_DIR}")

        # List them
        print("\nConfigs now available:")
        for f in OUTPUT_DIR.glob("*.conf"):
            print(f"  - {f.name}")
    else:
        print("\n⚠️ No .conf files found in Downloads.")
        print(f"Please download from: https://account.protonvpn.com/downloads")
        print(f"Save to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
