#!/bin/bash
# skills-autoupdate — daily pull --ff-only on every git-cloned skill.
#
# - Iterates over every <SKILLS_DIR>/*/.git/ directory
# - git fetch + git pull --ff-only origin main on each
# - Logs everything to <LOG_FILE>
# - If anything changed, notifies the notification target via msg-send
# - install.sh changes are notified but NOT re-run (manual decision)
#
# Env (set by the systemd unit at install time):
#   SKILLS_DIR  — directory of git-cloned skills (default: ~/.claude-fleet-starter/skills)
#   LOG_FILE    — where to append the run log
set -uo pipefail

LOG="${LOG_FILE:-${HOME:-/root}/.cache/claude-fleet/skills-autoupdate.log}"
SKILLS_DIR="${SKILLS_DIR:-${HOME:-/root}/.claude-fleet-starter/skills}"
mkdir -p "$(dirname "$LOG")"
HOST=$(hostname | tr '[:upper:]' '[:lower:]')

# Append + tee so the log is visible on stdout when running interactively
{
    echo
    echo "=== $(date -Iseconds) skills-autoupdate on ${HOST} ==="
} >> "$LOG"

updates=()
failures=()
installer_changes=()

for skill_dir in "$SKILLS_DIR"/*/; do
    [[ -d "$skill_dir/.git" ]] || continue
    skill=$(basename "$skill_dir")
    cd "$skill_dir" || continue

    before=$(git rev-parse HEAD 2>/dev/null || echo "unknown")

    # Fetch only — separate from pull so we can detect failures cleanly
    if ! git fetch origin --quiet 2>>"$LOG"; then
        echo "  [$skill] fetch FAILED" >> "$LOG"
        failures+=("$skill: fetch failed")
        continue
    fi

    # Try fast-forward only pull
    if git pull --ff-only origin main --quiet 2>>"$LOG"; then
        after=$(git rev-parse HEAD)
        if [[ "$before" != "$after" ]]; then
            short_before=${before:0:7}
            short_after=${after:0:7}
            echo "  [$skill] $short_before -> $short_after" >> "$LOG"

            # Detect install.sh changes (root-level OR scripts/install.sh)
            changed_files=$(git diff --name-only "$before" "$after" 2>/dev/null || echo "")
            if echo "$changed_files" | grep -qE "(^|/)install\.sh$"; then
                installer_changes+=("$skill")
                updates+=("$skill ($short_before → $short_after) — ⚠ install.sh modifié")
            else
                updates+=("$skill ($short_before → $short_after)")
            fi
        else
            echo "  [$skill] up to date" >> "$LOG"
        fi
    else
        echo "  [$skill] pull FAILED (non-fast-forward or conflict)" >> "$LOG"
        failures+=("$skill: pull non-fast-forward (modifs locales?)")
    fi
done

# Notify if anything changed or failed — but only if not on the notification host (configured via NOTIFY_HOST env, defaults to none)
# (the notification target reads its own log, no need to msg-send to self)
if [[ ${#updates[@]} -gt 0 || ${#failures[@]} -gt 0 ]]; then
    {
        echo "skills-autoupdate sur ${HOST} — $(date -Iseconds)"
        echo
        if [[ ${#updates[@]} -gt 0 ]]; then
            echo "Updates pull --ff-only OK :"
            for u in "${updates[@]}"; do
                echo "- $u"
            done
        fi
        if [[ ${#failures[@]} -gt 0 ]]; then
            echo
            echo "Échecs :"
            for f in "${failures[@]}"; do
                echo "- $f"
            done
        fi
        if [[ ${#installer_changes[@]} -gt 0 ]]; then
            echo
            echo "⚠ install.sh modifié pour : ${installer_changes[*]}"
            echo "(NON rerun automatiquement — à exécuter manuellement si pertinent)"
        fi
    } > /tmp/skills-autoupdate-notif-$$.md

    if [[ -n "${NOTIFY_HOST:-}" && "$HOST" != "${NOTIFY_HOST}" ]] && command -v msg-send >/dev/null 2>&1; then
        n=${#updates[@]}
        msg-send "${NOTIFY_HOST}" \
            --subject "auto-pull ${HOST}: ${n} skill(s) updated" \
            --body /tmp/skills-autoupdate-notif-$$.md >> "$LOG" 2>&1 || true
    fi
    cat /tmp/skills-autoupdate-notif-$$.md >> "$LOG"
    rm -f /tmp/skills-autoupdate-notif-$$.md
fi

echo "done" >> "$LOG"
