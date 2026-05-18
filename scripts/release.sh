#!/usr/bin/env bash
# N-Xyme MIND Release Script
# Usage: ./scripts/release.sh v0.1.0

set -euo pipefail

VERSION="${1:-}"
REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
cd "$REPO_ROOT"

if [ -z "$VERSION" ]; then
    echo "Usage: ./scripts/release.sh v0.5.0"
    echo ""
    echo "Current tags:"
    git tag --sort=-v:refname 2>/dev/null | head -5 || echo "  (no tags yet)"
    exit 1
fi

# Validate version format
if ! echo "$VERSION" | grep -qE '^v[0-9]+\.[0-9]+\.[0-9]+'; then
    echo "Error: Version must match semver pattern vX.Y.Z (e.g., v0.5.0)"
    exit 1
fi

echo "═══════════════════════════════════════════"
echo "  N-Xyme MIND — Release $VERSION"
echo "═══════════════════════════════════════════"
echo ""

# 1. Ensure working directory is clean
if ! git diff --quiet; then
    echo "❌ Working directory has unstaged changes. Commit or stash first."
    exit 1
fi

# 2. Run release check
echo ">>> [1/5] Running release readiness check..."
echo ""
if ! bash scripts/release-check.sh; then
    echo ""
    echo "❌ Release check failed. Fix issues and retry."
    exit 1
fi
echo ""

# 3. Update CHANGELOG
echo ">>> [2/5] CHANGELOG update..."
echo ""
if [ ! -f CHANGELOG.md ]; then
    echo "WARNING: CHANGELOG.md does not exist. Creating placeholder."
    cat > CHANGELOG.md <<- EOF
# Changelog

## $VERSION — $(date +%Y-%m-%d)

### Added
- Placeholder for new features

### Fixed
- Placeholder for bug fixes

### Changed
- Placeholder for changes

EOF
    git add CHANGELOG.md
    git commit -m "docs: initialize CHANGELOG.md for $VERSION"
    echo "CHANGELOG.md created."
fi

echo "Please update CHANGELOG.md with the $VERSION changes, save the file, then press ENTER to continue."
read -r
echo ""

# 4. Build binaries
echo ">>> [3/5] Building binaries..."
mkdir -p dist
if which mojo &>/dev/null; then
    MOJO_TARGETS=(
        "services/mojo/src/main.mojo:dist/nx-engine-linux"
        "services/mojo/src/compat.mojo:dist/nx-compat-linux"
    )
    for entry in "${MOJO_TARGETS[@]}"; do
        src="${entry%%:*}"
        dst="${entry##*:}"
        if [ -f "$src" ]; then
            echo "  Building $src -> $dst"
            mojo build "$src" -o "$dst" 2>/dev/null && \
                echo "  ✅ Built $dst" || \
                echo "  ⚠️  Build failed for $src (CI will handle)"
        fi
    done
else
    echo "  ⚠️  Mojo not installed locally — CI will build binaries"
fi
echo ""

# 5. Create git tag
echo ">>> [4/5] Creating tag $VERSION..."
git tag -a "$VERSION" -m "Release $VERSION"
echo ""

# 6. Push
echo ">>> [5/5] Pushing to origin..."
echo "  Pushing commit and tag: $VERSION"
git push origin HEAD --tags
echo ""

echo "═══════════════════════════════════════════"
echo "  ✅ Release $VERSION complete"
echo "═══════════════════════════════════════════"
echo ""
echo "Next steps:"
echo "  1. Create GitHub Release:"
echo "     https://github.com/nxyme/N-Xyme_MIND/releases/new?tag=$VERSION"
echo "  2. Attach binaries from dist/"
echo "  3. Write release notes referencing CHANGELOG.md"
echo ""
