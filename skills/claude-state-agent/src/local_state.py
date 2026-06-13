"""Generate this machine's full state — entirely local, no SSH.

Reads:
  - the local tmux "claude" session pane
  - /proc/pressure/* (PSI)
  - tailnet-messaging inbox (via msg-list --json) if the skill is installed
"""
from __future__ import annotations

import json
import socket
import subprocess
import time
from pathlib import Path

from .models import LocalState, PromptInfo, TransferSummary
from .parser import (detect_state_label, parse_permission_prompt,
                     parse_session_url, remote_control_active)
from .pressure import parse_pressure

TMUX_SESSION = "claude"
PANE_LINES = 50
MSG_LIST_BIN = "/usr/local/bin/msg-list"


def _hostname() -> str:
    try:
        out = subprocess.check_output(["tailscale", "status", "--self", "--json"],
                                       timeout=5, text=True)
        return json.loads(out)["Self"].get("HostName", socket.gethostname()).lower()
    except Exception:
        return socket.gethostname().lower()


_HOST = _hostname()


def _capture_pane() -> str | None:
    """Capture the local tmux 'claude' pane. None if no session.

    Combines the current visible screen (no -S flag) with recent scrollback
    (-S -PANE_LINES) so that both interactive overlays (permission prompts) and
    scrolled-off content (RC banner) are visible to the parser.
    """
    try:
        # Visible screen first — catches TUI overlays (permission prompts)
        r_vis = subprocess.run(
            ["tmux", "capture-pane", "-t", TMUX_SESSION, "-p"],
            capture_output=True, text=True, timeout=5,
        )
        # Scrollback — catches banners that may have scrolled off screen
        r_scroll = subprocess.run(
            ["tmux", "capture-pane", "-t", TMUX_SESSION, "-p", "-S", f"-{PANE_LINES}"],
            capture_output=True, text=True, timeout=5,
        )
        if r_vis.returncode != 0 and r_scroll.returncode != 0:
            return None
        return (r_vis.stdout or "") + "\n" + (r_scroll.stdout or "")
    except Exception:
        return None


def _has_tmux_session() -> bool:
    try:
        r = subprocess.run(["tmux", "has-session", "-t", TMUX_SESSION],
                           capture_output=True, timeout=5)
        return r.returncode == 0
    except Exception:
        return False


def _read_pressure() -> str | None:
    """Read PSI files locally."""
    try:
        parts = []
        for label, path in [("IO", "/proc/pressure/io"),
                             ("CPU", "/proc/pressure/cpu"),
                             ("MEM", "/proc/pressure/memory")]:
            parts.append(label)
            try:
                parts.append(Path(path).read_text())
            except Exception:
                pass
        parts.append("LOAD")
        parts.append(Path("/proc/loadavg").read_text())
        return "\n".join(parts)
    except Exception:
        return None


def _read_transfers() -> tuple[int, list[TransferSummary]]:
    """Read inbox transfers via msg-list --json (tailnet-messaging skill)."""
    if not Path(MSG_LIST_BIN).exists():
        return 0, []
    try:
        r = subprocess.run([MSG_LIST_BIN, "--json"], capture_output=True, text=True, timeout=10)
        if r.returncode != 0:
            return 0, []
        data = json.loads(r.stdout)
        transfers = []
        for t in data.get("transfers", []):
            atts = [f for f in t.get("files", []) if not f.endswith(".md")]
            transfers.append(TransferSummary(
                id=t["id"], sender=t.get("sender"), subject=t.get("subject"),
                priority=t.get("priority"), attachments=atts,
            ))
        return data.get("count", len(transfers)), transfers
    except Exception:
        return 0, []


def get_local_state() -> LocalState:
    """Build the full local state of this machine."""
    state = LocalState(host=_HOST, generated_at=time.time())

    state.tmux_session = _has_tmux_session()
    pane = _capture_pane() if state.tmux_session else None

    if pane is not None:
        label = detect_state_label(pane)
        state.state_label = label
        state.session_url = parse_session_url(pane)
        if label in ("ready_with_remote_control", "ready_no_remote_control",
                     "ready_unknown_remote_control", "permission_prompt",
                     "resume_picker", "resume_mode_choice", "trust_folder",
                     "oauth_pending", "busy", "starting"):
            state.claude_running = True
        # Detected independently of the label so it stays correct while busy.
        state.remote_control = remote_control_active(pane)
        if label == "permission_prompt":
            state.prompt = parse_permission_prompt(pane)
        else:
            state.prompt = PromptInfo(active=False)
    else:
        state.state_label = "no_tmux"

    # Pressure (always available, even if claude is down)
    state.pressure = parse_pressure(_read_pressure())

    # Transfers
    count, transfers = _read_transfers()
    state.transfers_unread = count
    state.transfers = transfers

    return state
