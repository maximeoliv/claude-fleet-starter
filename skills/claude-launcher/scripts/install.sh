#!/bin/bash
# Installs claude-launcher as a systemd service. Idempotent.
set -e

UNIT_SRC="$(dirname "$(realpath "$0")")/../systemd/claude-launcher.service"
UNIT_DST="/etc/systemd/system/claude-launcher.service"

if [[ ! -f "$UNIT_SRC" ]]; then
    echo "ERROR: unit file not found at $UNIT_SRC" >&2
    exit 1
fi

# Copy unit (or update if changed)
if [[ ! -f "$UNIT_DST" ]] || ! cmp -s "$UNIT_SRC" "$UNIT_DST"; then
    cp "$UNIT_SRC" "$UNIT_DST"
    chmod 644 "$UNIT_DST"
    echo "Installed $UNIT_DST"
    systemctl daemon-reload
else
    echo "$UNIT_DST already up-to-date"
fi

# Enable (does not start)
systemctl enable claude-launcher.service 2>&1 | grep -v 'Created symlink' || true

# Install claude-fork wrapper in /usr/local/bin
SCRIPT_DIR="$(dirname "$(realpath "$0")")"
ln -sf "$SCRIPT_DIR/claude-fork" /usr/local/bin/claude-fork
echo "✓ /usr/local/bin/claude-fork → $SCRIPT_DIR/claude-fork"

# Verify
if systemctl is-enabled claude-launcher.service >/dev/null 2>&1; then
    echo "✓ claude-launcher.service is enabled (will fire at next boot)"
else
    echo "✗ claude-launcher.service is NOT enabled" >&2
    exit 1
fi

echo
echo "Test now (without rebooting):"
echo "  systemctl start claude-launcher.service"
echo "  tmux list-sessions   # should show 'claude'"
echo "  tmux attach -t claude   # see live UI"
