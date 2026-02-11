#!/bin/sh
set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HOOK_SRC="$REPO_ROOT/tools/hooks/pre-commit"
HOOK_DST="$REPO_ROOT/.git/hooks/pre-commit"

if [ ! -d "$REPO_ROOT/.git" ]; then
  echo "❌ Not a git repo: $REPO_ROOT"
  exit 1
fi

if [ ! -f "$HOOK_SRC" ]; then
  echo "❌ Missing hook template: $HOOK_SRC"
  exit 1
fi

mkdir -p "$REPO_ROOT/.git/hooks"
cp "$HOOK_SRC" "$HOOK_DST"
chmod +x "$HOOK_DST"

echo "✅ Installed pre-commit hook to: $HOOK_DST"
echo ""
echo "Test it with:"
echo "  $HOOK_DST"
