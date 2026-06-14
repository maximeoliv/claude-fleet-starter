#!/usr/bin/env bash
# claude-fleet-starter — interactive installer
#
# This script:
#   1. Detects your OS and language
#   2. Asks you what you want to install (with explanations adapted to your level)
#   3. Installs Claude Code (if not already there), Tailscale (if you want), and the skills
#   4. Sets up systemd services / launchd agents / start scripts depending on your OS
#   5. Lets you bootstrap from your existing Claude Cowork / Claude Code history if you have one
#
# Usage:
#   bash install.sh             # interactive
#   bash install.sh --quiet     # use defaults, less prompts (for experienced users)
#   bash install.sh --uninstall # remove everything
#
# License: MIT
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="${INSTALL_DIR:-$HOME/.claude-fleet-starter}"

# ── 0. Language detection (i18n) ──────────────────────────────────────────────
# Tries $LANG env var first, falls back to 'en'. User can override with --lang=fr/en.
# NOTE: ${LANG:-} guards against `set -u` crashing when $LANG is unset.
_LANG_RAW="${LANG:-}"
LANG_CODE="${_LANG_RAW:0:2}"
case "$LANG_CODE" in
    fr|en) ;;
    *) LANG_CODE="en" ;;
esac
for arg in "$@"; do
    case "$arg" in
        --lang=fr) LANG_CODE="fr" ;;
        --lang=en) LANG_CODE="en" ;;
    esac
done

# Load translations
# shellcheck disable=SC1090
source "$SCRIPT_DIR/lib/i18n/${LANG_CODE}.sh"

# ── 1. Helpers ───────────────────────────────────────────────────────────────
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib/detect-os.sh"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib/doctor.sh"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib/prompts.sh"

# ── 2. Wizard ────────────────────────────────────────────────────────────────
print_header

# Pre-flight: detect OS
OS_NAME="$(detect_os)"
say "$T_OS_DETECTED" "$OS_NAME"

# Adapt verbosity based on detected user level (heuristic)
# By default: medium verbosity. User can say "détaille plus" / "va plus vite" via Claude later.
VERBOSITY="${VERBOSITY:-medium}"

# Pre-flight: check dependencies
say "$T_CHECKING_DEPS"
doctor_check_basic || {
    err "$T_DEPS_MISSING"
    exit 1
}

# Step 1: Claude Code
if command -v claude >/dev/null 2>&1; then
    CLAUDE_VERSION="$(claude --version 2>&1 | head -1)"
    say "$T_CLAUDE_FOUND" "$CLAUDE_VERSION"
else
    if confirm "$T_INSTALL_CLAUDE"; then
        say "$T_INSTALLING_CLAUDE"
        curl -fsSL https://claude.ai/install.sh | bash
        # Add ~/.local/bin to PATH in .bashrc only if not already there (idempotent).
        # shellcheck disable=SC2016
        if ! grep -qsF 'HOME/.local/bin:$PATH' "$HOME/.bashrc"; then
            # shellcheck disable=SC2016
            echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
        fi
        export PATH="$HOME/.local/bin:$PATH"
        say "$T_CLAUDE_INSTALLED"
    else
        say "$T_CLAUDE_SKIPPED"
    fi
fi

# Step 2: Tailscale (optional but strongly recommended for multi-machine)
TAILSCALE_INSTALLED=0
if command -v tailscale >/dev/null 2>&1; then
    TAILSCALE_INSTALLED=1
    say "$T_TAILSCALE_FOUND"
else
    explain "$T_TAILSCALE_WHAT"
    if confirm "$T_INSTALL_TAILSCALE"; then
        say "$T_INSTALLING_TAILSCALE"
        curl -fsSL https://tailscale.com/install.sh | sh
        TAILSCALE_INSTALLED=1
        say "$T_TAILSCALE_AUTH_NEEDED"
        # Auth will be triggered when user runs `tailscale up` themselves — we give them the command
        echo
        echo "  sudo tailscale up --ssh"
        echo
        say "$T_PRESS_ENTER_WHEN_DONE"
        read -r
    fi
fi

# Step 3: Remote Control
explain "$T_RC_WHAT"
say "$T_RC_SECURITY_WARNING"
if confirm "$T_ENABLE_RC_AUTOSTART"; then
    ENABLE_RC=1
else
    ENABLE_RC=0
fi

# Step 4: Skills to install
say "$T_SKILLS_QUESTION"
explain "$T_SKILLS_LIST"

# Default: all essential skills. User can opt-out interactively.
declare -A SKILLS_TO_INSTALL=(
    [tailnet-messaging]=1
    [claude-state-agent]=1
    [claude-launcher]=1
    [cerveau]=1
    [tailscale-secure-form]=1
    [skills-autoupdate]=1
    [onboard-tailnet-machine]=1
    [claude-on-remote]=1
)

# Step 5: Memory starter
if confirm "$T_INSTALL_MEMORY_STARTER"; then
    INSTALL_MEMORY=1
else
    INSTALL_MEMORY=0
fi

# Step 6: Bootstrap from history
say "$T_BOOTSTRAP_QUESTION"
explain "$T_BOOTSTRAP_WHAT"
HISTORY_PATH=""
if confirm "$T_BOOTSTRAP_HAS_HISTORY"; then
    say "$T_BOOTSTRAP_PATH_PROMPT"
    read -r HISTORY_PATH
    if [[ -n "$HISTORY_PATH" && ! -e "$HISTORY_PATH" ]]; then
        warn "$T_BOOTSTRAP_PATH_INVALID" "$HISTORY_PATH"
        HISTORY_PATH=""
    fi
fi

# ── 3. Install ────────────────────────────────────────────────────────────────

mkdir -p "$INSTALL_DIR"
cp -r "$SCRIPT_DIR/skills" "$INSTALL_DIR/"
cp -r "$SCRIPT_DIR/lib" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/install.sh" "$INSTALL_DIR/"

if [[ "$INSTALL_MEMORY" == "1" ]]; then
    mkdir -p "$HOME/.claude/projects/-${HOME//\//-}/memory"
    cp -n "$SCRIPT_DIR/memory-starter/"*.md "$HOME/.claude/projects/-${HOME//\//-}/memory/" || true
    say "$T_MEMORY_INSTALLED"
fi

# Install each enabled skill
for skill in "${!SKILLS_TO_INSTALL[@]}"; do
    if [[ "${SKILLS_TO_INSTALL[$skill]}" == "1" && -d "$INSTALL_DIR/skills/$skill" ]]; then
        say "$T_INSTALLING_SKILL" "$skill"
        if [[ -f "$INSTALL_DIR/skills/$skill/install.sh" ]]; then
            (cd "$INSTALL_DIR/skills/$skill" && bash install.sh)
        elif [[ -f "$INSTALL_DIR/skills/$skill/scripts/install.sh" ]]; then
            (cd "$INSTALL_DIR/skills/$skill" && bash scripts/install.sh)
        fi
    fi
done

# Setup Claude Code autostart with RC if requested
if [[ "$ENABLE_RC" == "1" ]]; then
    say "$T_SETTING_UP_RC_AUTOSTART"
    # Use claude-launcher if installed
    if [[ -d "$INSTALL_DIR/skills/claude-launcher" ]]; then
        : # claude-launcher already handles this in its install.sh
    fi
fi

# Bootstrap from history if path provided
if [[ -n "$HISTORY_PATH" ]]; then
    say "$T_BOOTSTRAP_RUNNING"
    say "$T_BOOTSTRAP_INSTRUCTIONS" "$HISTORY_PATH"
    # The actual bootstrap is a prompt in bootstrap/analyze-history.md — the user feeds it to Claude.
fi

# ── 4. Done ──────────────────────────────────────────────────────────────────
print_done_banner

say "$T_NEXT_STEPS"
echo
echo "  - claude --remote-control mon-nom-machine"
echo "  - $INSTALL_DIR/skills/cerveau/scripts/cerveau-list"
echo "  - msg-send --help"
echo

if [[ -z "${TAILSCALE_INSTALLED:-}" || "$TAILSCALE_INSTALLED" != "1" ]]; then
    warn "$T_TAILSCALE_REMINDER"
fi

say "$T_DOCS"
echo "  https://github.com/maximeoliv/claude-fleet-starter"
