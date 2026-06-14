#!/bin/bash
# Launches a tmux session "claude" and starts claude code inside, with remote-control
# enabled and the latest conversation in $HOME auto-resumed.
# Designed to be invoked by claude-launcher.service at boot (the unit sets HOME=
# to the install user's home, see claude-launcher/scripts/install.sh).
set -e

SESSION="claude"
# CWD = the install user's $HOME. `claude -c` resumes the conversation rooted
# at this dir, so it MUST match the user's project dir (NOT /root for a non-root
# install — that would either fail or resume the wrong fil).
CWD="${HOME:-/root}"
HOSTNAME=$(hostname | tr '[:upper:]' '[:lower:]')

# Resolve the claude binary with an absolute path — the tmux shell may not have
# ~/.local/bin in its PATH (observed on fastpanel), which made `claude` not found.
CLAUDE_BIN=""
for cand in "$(command -v claude 2>/dev/null)" "$HOME/.local/bin/claude" /usr/local/bin/claude /usr/bin/claude; do
    if [[ -n "$cand" && -x "$cand" ]]; then CLAUDE_BIN="$cand"; break; fi
done
[[ -z "$CLAUDE_BIN" ]] && CLAUDE_BIN="claude"  # last-resort fallback

# Skip if a tmux session "claude" is already running (e.g. user pre-launched it)
if tmux has-session -t "$SESSION" 2>/dev/null; then
    echo "tmux session '$SESSION' already exists — skipping launch"
    exit 0
fi

# Create detached tmux session in $HOME
tmux new-session -d -s "$SESSION" -x 200 -y 50 -c "$CWD"
echo "tmux session '$SESSION' created in $CWD"

# Force a valid UTF-8 locale before launching claude. Some machines have a broken
# locale (e.g. n8n: fr_FR.UTF-8 not generated) which crashes the claude TUI.
# C.UTF-8 is universally available.
tmux send-keys -t "$SESSION" "export LANG=C.UTF-8 LC_ALL=C.UTF-8" Enter

# Build the claude command: try --continue first, fallback to fresh start
# If --continue fails (no prior conversation in cwd), claude exits non-zero and
# the second command runs in the same tmux pane.
CMD="$CLAUDE_BIN -c --remote-control \"$HOSTNAME\" || $CLAUDE_BIN --remote-control \"$HOSTNAME\""
tmux send-keys -t "$SESSION" "$CMD" Enter

echo "Sent: $CMD"

# Wait for claude to render UI, then auto-accept trust folder prompt if shown.
# Trust state is sometimes not persisted across reboots, so we always check.
sleep 8
if tmux capture-pane -t "$SESSION" -p -S -30 | grep -q "I trust this folder"; then
    tmux send-keys -t "$SESSION" Enter
    echo "Auto-accepted trust folder prompt"
fi

# Drive claude past any remaining startup prompt (resume_mode_choice, etc.)
# to fully ready, via the local claude-state-agent. Without this step, the
# launcher only starts claude — claude then sits on the resume picker and
# stays "stuck" until someone runs ensure_ready manually (cf. the May 17
# and May 20 host crashes, which both required manual fleet recovery).
# The agent enforces full-as-is resume only — never from-summary.
LOCAL_IP=$(tailscale ip -4 2>/dev/null | head -1)
if [[ -n "$LOCAL_IP" ]]; then
    # Wait up to 60s for the local agent to come up
    for _ in $(seq 1 12); do
        if curl -s --max-time 2 "http://$LOCAL_IP:18920/state" >/dev/null 2>&1; then
            echo "claude-state-agent reachable on $LOCAL_IP:18920 — driving to ready..."
            curl -s --max-time 130 -X POST "http://$LOCAL_IP:18920/claude/ensure-ready" \
                > /tmp/claude-launcher-ensure-ready.log 2>&1 \
                && echo "ensure-ready done" \
                || echo "ensure-ready returned non-zero (see /tmp/claude-launcher-ensure-ready.log)"
            break
        fi
        sleep 5
    done
else
    echo "WARN: no tailnet IP found — skipping ensure-ready"
fi

# Launch additional sessions from ~/.claude-sessions.json (if present)
EXTRA_SESSIONS_CONFIG="$HOME/.claude-sessions.json"
if [[ -f "$EXTRA_SESSIONS_CONFIG" ]]; then
    echo "Reading extra sessions from $EXTRA_SESSIONS_CONFIG..."
    python3 - <<PYEOF
import json, subprocess, time, sys, urllib.request

import os as _os
config_path = "$EXTRA_SESSIONS_CONFIG"
local_ip = "$LOCAL_IP"
claude_bin = "$CLAUDE_BIN"
default_cwd = _os.path.expanduser("~")

with open(config_path) as f:
    config = json.load(f)

for sess in config.get("sessions", []):
    name = sess.get("name")
    cwd = sess.get("cwd", default_cwd)
    cmd = sess.get("cmd")
    autostart = sess.get("autostart", True)

    if not autostart or not name:
        continue

    # Use claude_bin if cmd starts with "claude "
    if cmd and cmd.startswith("claude "):
        cmd = claude_bin + cmd[6:]
    elif not cmd:
        cmd = f"{claude_bin} -c --remote-control {name}"

    r = subprocess.run(["tmux", "has-session", "-t", name], capture_output=True)
    if r.returncode == 0:
        print(f"  tmux session '{name}' already exists — skipping")
        continue

    confirm_prompt = sess.get("confirm_prompt")  # text to wait for before sending Enter

    subprocess.run(["tmux", "new-session", "-d", "-s", name, "-x", "200", "-y", "50", "-c", cwd])
    subprocess.run(["tmux", "send-keys", "-t", name, "export LANG=C.UTF-8 LC_ALL=C.UTF-8", "Enter"])
    subprocess.run(["tmux", "send-keys", "-t", name, cmd, "Enter"])
    print(f"  Started session '{name}' in {cwd}")

    # If confirm_prompt set, wait for that text in the pane then send Enter
    if confirm_prompt:
        for _ in range(20):
            time.sleep(2)
            r = subprocess.run(["tmux", "capture-pane", "-t", name, "-p", "-S", "-10"],
                               capture_output=True, text=True)
            if confirm_prompt in r.stdout:
                subprocess.run(["tmux", "send-keys", "-t", name, "", "Enter"])
                print(f"  Auto-confirmed prompt '{confirm_prompt[:40]}' in session '{name}'")
                break

    if local_ip:
        # Use ensure-ready-session endpoint
        url = f"http://{local_ip}:18920/sessions/{name}/ensure-ready"
        for attempt in range(24):
            try:
                resp = urllib.request.urlopen(url, data=b"", timeout=130)
                result = json.loads(resp.read())
                print(f"  Session '{name}' ensure-ready: {result.get('final_state', 'done')}")
                break
            except Exception as e:
                if attempt < 11:
                    time.sleep(5)
                else:
                    print(f"  WARN: ensure-ready for '{name}' failed: {e}")
PYEOF
fi

echo "Inspect with: tmux attach -t $SESSION"
