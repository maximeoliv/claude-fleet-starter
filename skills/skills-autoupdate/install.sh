#!/bin/bash
# Install skills-autoupdate as a systemd timer that runs daily at 04:00.
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"

# Make script executable
chmod +x "$DIR/scripts/autoupdate.sh"

# Install systemd units (symlinks so git updates propagate to systemd)
ln -sf "$DIR/systemd/skills-autoupdate.service" /etc/systemd/system/skills-autoupdate.service
ln -sf "$DIR/systemd/skills-autoupdate.timer" /etc/systemd/system/skills-autoupdate.timer

systemctl daemon-reload
systemctl enable --now skills-autoupdate.timer

# Make sure the log file exists with the right permissions
touch /var/log/skills-autoupdate.log

echo "=============================================="
echo "skills-autoupdate installed."
echo "Timer status: $(systemctl is-active skills-autoupdate.timer)"
echo "Next run:     $(systemctl show skills-autoupdate.timer --property=NextElapseUSecRealtime --value)"
echo "Log file:     /var/log/skills-autoupdate.log"
echo ""
echo "Run manually:  systemctl start skills-autoupdate.service"
echo "Disable:       systemctl disable --now skills-autoupdate.timer"
echo "=============================================="
