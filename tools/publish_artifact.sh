#!/usr/bin/env bash
# Publish a local Claude artifact HTML file as a public page with working
# Open Graph tags, so pasting its URL in Slack unfurls correctly.
#
# Usage:
#   tools/publish_artifact.sh <input.html> <slug> [--title "..."] [--description "..."] [--no-push]
#
# <slug> becomes the URL path: https://alexwhitela.github.io/artifact-share/a/<slug>/

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PAGES_BASE="https://alexwhitela.github.io/artifact-share"

if [ $# -lt 2 ]; then
  echo "Usage: $0 <input.html> <slug> [--title \"...\"] [--description \"...\"] [--no-push]" >&2
  exit 1
fi

INPUT="$1"; shift
SLUG="$1"; shift

if [[ ! "$SLUG" =~ ^[a-z0-9][a-z0-9-]*$ ]]; then
  echo "Slug must be lowercase letters/numbers/hyphens (got: $SLUG)" >&2
  exit 1
fi

if [ ! -f "$INPUT" ]; then
  echo "No such file: $INPUT" >&2
  exit 1
fi

PUSH=1
TITLE_ARGS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --title) TITLE_ARGS+=(--title "$2"); shift 2 ;;
    --description) TITLE_ARGS+=(--description "$2"); shift 2 ;;
    --no-push) PUSH=0; shift ;;
    *) echo "Unknown argument: $1" >&2; exit 1 ;;
  esac
done

PAGE_URL="$PAGES_BASE/a/$SLUG/"
OUT_DIR="$REPO_ROOT/a/$SLUG"
mkdir -p "$OUT_DIR"

python3 "$SCRIPT_DIR/og_tags.py" inject "$INPUT" --url "$PAGE_URL" "${TITLE_ARGS[@]}" -o "$OUT_DIR/index.html"

echo "--- validation ---"
python3 "$SCRIPT_DIR/og_tags.py" validate "$OUT_DIR/index.html"
echo "------------------"

cd "$REPO_ROOT"
git add "a/$SLUG/index.html"
if git diff --cached --quiet; then
  echo "No changes to commit (identical to last published version)."
else
  git commit -m "Publish artifact: $SLUG"
fi

if [ "$PUSH" -eq 1 ]; then
  git push
  echo
  echo "Pushed. GitHub Pages takes ~30-60s to redeploy after a push."
  echo "Check deploy status: https://github.com/alexwhitela/artifact-share/deployments"
else
  echo
  echo "Committed locally, not pushed (--no-push). Run 'git push' from $REPO_ROOT when ready."
fi

echo
echo "Public URL (paste this into Slack):"
echo "  $PAGE_URL"
