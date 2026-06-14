#!/usr/bin/env bash
# claude-fleet-starter — uninstall script (Linux / macOS / Synology DSM).
#
# What it does:
#   1. Stops + disables systemd services we installed
#      (claude-state-agent, claude-launcher, skills-autoupdate.timer, ...)
#   2. Removes the systemd unit files under /etc/systemd/system/.
#   3. Deletes symlinks the install created in /usr/local/bin/ for our skills.
#   4. Asks before deleting user data (memories, second brain, inbox, token file).
#   5. Leaves Claude Code itself and Tailscale alone — you might want to keep them.
#
# Usage:
#   bash uninstall.sh              # interactive
#   bash uninstall.sh --keep-data  # remove services/binaries but keep ~/.claude/ + ~/inbox + ~/cerveau-flotte
#   bash uninstall.sh --yes        # non-interactive, removes EVERYTHING (services + data)
set -euo pipefail

INSTALL_DIR="${INSTALL_DIR:-$HOME/.claude-fleet-starter}"
KEEP_DATA=0
YES=0
for arg in "$@"; do
    case "$arg" in
        --keep-data) KEEP_DATA=1 ;;
        --yes|-y) YES=1 ;;
    esac
done

if command -v sudo >/dev/null 2>&1 && [[ $EUID -ne 0 ]]; then
    SUDO="sudo"
else
    SUDO=""
fi

C_RESET='\033[0m'; C_BOLD='\033[1m'; C_DIM='\033[2m'; C_YELLOW='\033[33m'; C_RED='\033[31m'
[[ ! -t 1 ]] && { C_RESET=; C_BOLD=; C_DIM=; C_YELLOW=; C_RED=; }

confirm() {
    [[ "$YES" == "1" ]] && return 0
    printf "${C_BOLD}%s${C_RESET} [y/N] " "$1"
    read -r ans
    [[ "${ans,,}" =~ ^(y|yes|o|oui)$ ]]
}

printf "${C_BOLD}claude-fleet-starter uninstall${C_RESET}\n"
printf "${C_DIM}Install dir: %s${C_RESET}\n\n" "$INSTALL_DIR"

# 1. systemd services
SERVICES=(claude-state-agent.service claude-launcher.service skills-autoupdate.timer skills-autoupdate.service tailscale-secure-form.service)
for svc in "${SERVICES[@]}"; do
    if systemctl list-unit-files 2>/dev/null | grep -q "^${svc}"; then
        printf "• Stopping + disabling %s\n" "$svc"
        $SUDO systemctl disable --now "$svc" 2>/dev/null || true
        $SUDO rm -f "/etc/systemd/system/$svc"
    fi
done
$SUDO systemctl daemon-reload 2>/dev/null || true

# 2. symlinks installed in /usr/local/bin (only ones we know we created)
SHORTCUTS=(msg-send msg-receive msg-list msg-show msg-archive msg-list-sessions cerveau cerveau-list cerveau-search cerveau-add)
for s in "${SHORTCUTS[@]}"; do
    if [[ -L "/usr/local/bin/$s" ]]; then
        target="$(readlink -f "/usr/local/bin/$s" 2>/dev/null || true)"
        if [[ "$target" == "$INSTALL_DIR/"* ]]; then
            printf "• Removing symlink /usr/local/bin/%s\n" "$s"
            $SUDO rm -f "/usr/local/bin/$s"
        fi
    fi
done

# 3. user data (gated)
if [[ "$KEEP_DATA" == "1" ]]; then
    printf "\n${C_YELLOW}Data kept: ~/.claude/, ~/inbox/, ~/cerveau-flotte/ (use --yes to remove them too).${C_RESET}\n"
else
    printf "\n"
    if confirm "Delete the kit install dir ${INSTALL_DIR} (incl. state-agent.env / token)?"; then
        rm -rf "$INSTALL_DIR"
        printf "  ✓ %s removed\n" "$INSTALL_DIR"
    fi
    if confirm "Delete the inbox at $HOME/inbox/ (received tailnet messages)?"; then
        rm -rf "$HOME/inbox"
        printf "  ✓ ~/inbox removed\n"
    fi
    if confirm "Delete the second brain at $HOME/cerveau-flotte/ (shared notes — irreversible!)?"; then
        rm -rf "$HOME/cerveau-flotte"
        printf "  ✓ ~/cerveau-flotte removed\n"
    fi
    if confirm "Delete the Claude Code memory dir under $HOME/.claude/projects/-${HOME//\//-}/memory/?"; then
        rm -rf "$HOME/.claude/projects/-${HOME//\//-}/memory"
        printf "  ✓ memory dir removed\n"
    fi
fi

printf "\n${C_BOLD}✓ Uninstall complete.${C_RESET}\n"
printf "${C_DIM}Claude Code and Tailscale were left in place. Remove them with your package manager if desired.${C_RESET}\n"
