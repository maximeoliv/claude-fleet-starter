#!/bin/bash
# Installs claude-launcher as a systemd user-aware service. Idempotent.
#
# Renders the unit's __USER__/__HOME__/__SCRIPTS_DIR__ placeholders so the
# service runs as the user who ran the install (not hardcoded root).
set -euo pipefail

SCRIPT_DIR="$(dirname "$(realpath "$0")")"
UNIT_SRC="$SCRIPT_DIR/../systemd/claude-launcher.service"
UNIT_DST="/etc/systemd/system/claude-launcher.service"

if [[ ! -f "$UNIT_SRC" ]]; then
    echo "ERROR: unit file not found at $UNIT_SRC" >&2
    exit 1
fi

INSTALL_USER="${SUDO_USER:-${USER:-$(id -un)}}"
INSTALL_HOME="$(getent passwd "$INSTALL_USER" | cut -d: -f6)"
INSTALL_HOME="${INSTALL_HOME:-$HOME}"

if [[ $EUID -eq 0 ]]; then
    BIN_DIR=/usr/local/bin
    SUDO=""
else
    BIN_DIR="$INSTALL_HOME/.local/bin"
    mkdir -p "$BIN_DIR"
    if command -v sudo >/dev/null 2>&1; then
        SUDO=sudo
    else
        echo "⚠ sudo absent et tu n'es pas root — impossible d'installer le service systemd." >&2
        echo "  Le wrapper claude-fork sera installé, le service non. Tu pourras lancer claude" >&2
        echo "  manuellement avec scripts/launch.sh ou via tmux à la connexion." >&2
        SUDO=""
        SKIP_SYSTEMD=1
    fi
fi

# Render the unit file with placeholders.
TMP_UNIT="$(mktemp)"
sed \
    -e "s#__USER__#${INSTALL_USER}#g" \
    -e "s#__HOME__#${INSTALL_HOME}#g" \
    -e "s#__SCRIPTS_DIR__#${SCRIPT_DIR}#g" \
    "$UNIT_SRC" >"$TMP_UNIT"

if [[ "${SKIP_SYSTEMD:-0}" != "1" ]]; then
    # Install/update the rendered unit if changed
    if [[ ! -f "$UNIT_DST" ]] || ! $SUDO cmp -s "$TMP_UNIT" "$UNIT_DST"; then
        $SUDO install -m 0644 "$TMP_UNIT" "$UNIT_DST"
        echo "Installed $UNIT_DST"
        $SUDO systemctl daemon-reload
    else
        echo "$UNIT_DST already up-to-date"
    fi
    $SUDO systemctl enable claude-launcher.service 2>&1 | grep -v 'Created symlink' || true
fi
rm -f "$TMP_UNIT"

# Install claude-fork wrapper in $BIN_DIR
ln -sf "$SCRIPT_DIR/claude-fork" "$BIN_DIR/claude-fork"
echo "✓ $BIN_DIR/claude-fork → $SCRIPT_DIR/claude-fork"

# Verify
if [[ "${SKIP_SYSTEMD:-0}" != "1" ]]; then
    if $SUDO systemctl is-enabled claude-launcher.service >/dev/null 2>&1; then
        echo "✓ claude-launcher.service is enabled (will fire at next boot)"
    else
        echo "✗ claude-launcher.service is NOT enabled" >&2
        exit 1
    fi
fi

echo
echo "Test now (without rebooting):"
echo "  $SUDO systemctl start claude-launcher.service"
echo "  tmux list-sessions   # should show 'claude'"
echo "  tmux attach -t claude   # see live UI"

if [[ "$BIN_DIR" == "$INSTALL_HOME/.local/bin" ]] && ! echo ":${PATH:-}:" | grep -q ":$BIN_DIR:"; then
    echo
    echo "⚠ $BIN_DIR n'est pas dans ton PATH. Ajoute :"
    echo '  echo '\''export PATH="$HOME/.local/bin:$PATH"'\'' >> ~/.bashrc && source ~/.bashrc'
fi
