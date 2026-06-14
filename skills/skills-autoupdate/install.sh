#!/bin/bash
# Install skills-autoupdate as a systemd timer that runs daily at 04:00.
#
# Renders __USER__/__SKILLS_DIR__/__LOG__/__EXEC__ placeholders in the unit
# file based on the install user, so the timer runs as that user (root or not)
# and updates that user's skills dir. The log lands in ~/.cache/claude-fleet
# for non-root installs.
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
chmod +x "$DIR/scripts/autoupdate.sh"

INSTALL_USER="${SUDO_USER:-${USER:-$(id -un)}}"
INSTALL_HOME="$(getent passwd "$INSTALL_USER" | cut -d: -f6)"
INSTALL_HOME="${INSTALL_HOME:-$HOME}"

# Where this kit's skills actually live. Default = ~/.claude-fleet-starter/skills.
SKILLS_DIR="${SKILLS_DIR:-$INSTALL_HOME/.claude-fleet-starter/skills}"

if [[ $EUID -eq 0 ]]; then
    LOG_FILE=/var/log/skills-autoupdate.log
    SUDO=""
else
    LOG_FILE="$INSTALL_HOME/.cache/claude-fleet/skills-autoupdate.log"
    mkdir -p "$(dirname "$LOG_FILE")"
    if command -v sudo >/dev/null 2>&1; then
        SUDO=sudo
    else
        echo "⚠ sudo absent et tu n'es pas root — impossible d'installer le timer systemd." >&2
        echo "  Tu pourras lancer manuellement scripts/autoupdate.sh quand tu veux." >&2
        exit 0
    fi
fi

touch "$LOG_FILE"

# Render the service unit.
UNIT_SRC="$DIR/systemd/skills-autoupdate.service"
UNIT_DST="/etc/systemd/system/skills-autoupdate.service"
TIMER_SRC="$DIR/systemd/skills-autoupdate.timer"
TIMER_DST="/etc/systemd/system/skills-autoupdate.timer"

TMP_UNIT="$(mktemp)"
sed \
    -e "s#__USER__#${INSTALL_USER}#g" \
    -e "s#__SKILLS_DIR__#${SKILLS_DIR}#g" \
    -e "s#__LOG__#${LOG_FILE}#g" \
    -e "s#__EXEC__#${DIR}/scripts/autoupdate.sh#g" \
    -e "s#__HOME__#${INSTALL_HOME}#g" \
    "$UNIT_SRC" >"$TMP_UNIT"
$SUDO install -m 0644 "$TMP_UNIT" "$UNIT_DST"
$SUDO install -m 0644 "$TIMER_SRC" "$TIMER_DST"
rm -f "$TMP_UNIT"

$SUDO systemctl daemon-reload
$SUDO systemctl enable --now skills-autoupdate.timer

echo "=============================================="
echo "skills-autoupdate installed."
echo "Timer status: $($SUDO systemctl is-active skills-autoupdate.timer)"
echo "Next run:     $($SUDO systemctl show skills-autoupdate.timer --property=NextElapseUSecRealtime --value)"
echo "Skills dir:   $SKILLS_DIR"
echo "Log file:     $LOG_FILE"
echo ""
echo "Run manually:  $SUDO systemctl start skills-autoupdate.service"
echo "Disable:       $SUDO systemctl disable --now skills-autoupdate.timer"
echo "=============================================="
