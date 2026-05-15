#!/bin/bash
set -euo pipefail

OPEN_AFTER=false
for arg in "$@"; do
  case "$arg" in
    --open) OPEN_AFTER=true ;;
  esac
done

log() { printf "[%s] %s\n" "$(date '+%Y-%m-%d %H:%M:%S')" "$*"; }
cleanup() {
  if [[ -n "${TMP_DIR:-}" && -d "$TMP_DIR" ]]; then
    log "Cleaning up temporary directory: $TMP_DIR"
    rm -rf "$TMP_DIR" || true
  fi
}
trap cleanup EXIT

log "=== Step 1: Checking for uv ==="
if command -v uv >/dev/null 2>&1; then
    log "uv is already installed."
else
    log "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
    log "uv installed. PATH updated to include $HOME/.local/bin"
fi

log "=== Step 2: Moving extracted app into ~/Applications ==="
mkdir -p "$HOME/Applications"

# Change to the directory where this script is located
cd "$(dirname "$0")"
log "Changed to script directory: $(pwd)"

make setup

if [[ "$OPEN_AFTER" == true ]]; then
    log "=== Step 3: Opening DeltaSpread ==="
    open "$HOME/Applications/DeltaSpread.app"
fi

log "✅ Installation complete! The application is now in ~/Applications."
log "✅ You can close this terminal window."
