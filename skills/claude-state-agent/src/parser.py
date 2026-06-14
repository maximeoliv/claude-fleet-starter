"""Parse a tmux pane snapshot from claude code and extract state + prompt info."""
from __future__ import annotations

import re
from typing import Optional

from .models import ActionType, DangerLevel, PromptInfo

# Permission prompt header detection — matches English and French Claude Code UI
_PROMPT_RE = re.compile(
    r"Do you want to proceed\?"          # English
    r"|Toujours autoriser"               # French: "Always allow" button (unique to prompts)
    r"|Autoriser Claude\s+à",            # French: "Allow Claude to..."
    re.IGNORECASE,
)

# Action types — order matters (most specific first)
_ACTION_PATTERNS = [
    ("MCP",          re.compile(r"\bmcp__([a-z0-9_]+)__([a-z0-9_]+)", re.IGNORECASE)),
    ("Agent",        re.compile(r"^\s*Agent\(", re.MULTILINE)),
    ("NotebookEdit", re.compile(r"NotebookEdit\(([^)]+)\)")),
    ("Edit",         re.compile(r"\bEdit\(([^)]+)\)")),
    ("Write",        re.compile(r"\bWrite\(([^)]+)\)")),
    ("Read",         re.compile(r"\bRead\(([^)]+)\)")),
    ("WebFetch",     re.compile(r"WebFetch\(([^)]+)\)")),
    ("WebSearch",    re.compile(r"WebSearch\(([^)]+)\)")),
    ("Bash",         re.compile(r"^\s*Bash command\s*\n+\s*(\S[^\n]*)", re.MULTILINE)),
]

# Bash command shortcut: also catch "Bash(cmd)" inline form
_BASH_INLINE_RE = re.compile(r"\bBash\(([^)]+)\)")

# Dangerous Bash command patterns (case insensitive)
_DANGER_RE = re.compile(
    r"(?:^|[\s|;&])(rm\s+-?r|rm\s+-r?f|dd\s+if=|mkfs|fdisk|wipefs|>\s*/dev/sd|"
    r"chmod\s+-R\s+0?77\d|chown\s+-R|sudo\s+(?:rm|dd|mkfs|chmod|chown)|"
    r"kill(?:all)?\s+-9|shutdown|reboot|halt|poweroff|systemctl\s+(?:stop|disable|mask)|"
    r"truncate|>\s*/etc/|drop\s+(?:table|database)|delete\s+from)",
    re.IGNORECASE,
)

# Yellow-ish risky-but-common
_SUSPICIOUS_RE = re.compile(
    r"(?:^|[\s|;&])(systemctl|docker\s+(?:stop|rm)|git\s+push|git\s+reset\s+--hard|"
    r"npm\s+publish|cargo\s+publish|pip\s+install|apt\s+install)",
    re.IGNORECASE,
)

# Detect remote-control state from footer
# Body text form: "/remote-control is active" ; footer chip form: "Remote Control active"
_RC_ACTIVE_RE = re.compile(r"/remote-control is active|Remote Control active", re.IGNORECASE)
_RC_HINT_RE = re.compile(r"control this session from your phone", re.IGNORECASE)
_SESSION_URL_RE = re.compile(r"https?://claude\.ai/code/(session_[A-Za-z0-9]+)")

# Hostname banner detection — accept lowercase, mixed-case, with spaces
_HOSTNAME_BANNER_RE = re.compile(r"─\s*([A-Za-z][\w\s-]{0,40})\s*─")

# Prompt-related signals
_TRUST_FOLDER_RE = re.compile(r"Yes, I trust this folder", re.IGNORECASE)
_RESUME_PICKER_RE = re.compile(r"Resume session", re.IGNORECASE)
_RESUME_MODE_RE = re.compile(r"Resume from summary.*Resume full session as-is", re.IGNORECASE | re.DOTALL)
_OAUTH_RE = re.compile(r"(Browser didn|Paste code here|Login successful)", re.IGNORECASE)
_BUSY_RE = re.compile(r"esc to interrupt", re.IGNORECASE)
# Fresh-launch welcome banner: "Welcome to Claude Code" OR "Welcome to Opus/Sonnet/Haiku ..."
_WELCOME_RE = re.compile(r"Welcome to (?:Claude Code|Opus|Sonnet|Haiku)", re.IGNORECASE)
# Idle-ready footer hint — present whenever claude is at an idle prompt
_SHORTCUTS_RE = re.compile(r"\?\s+for shortcuts", re.IGNORECASE)


def detect_state_label(pane: str) -> str:
    """Returns a coarse-grained label for the current screen of claude code."""
    if not pane:
        return "unknown"
    if _TRUST_FOLDER_RE.search(pane):
        return "trust_folder"
    if _RESUME_PICKER_RE.search(pane) and "Search" in pane:
        return "resume_picker"
    if _RESUME_MODE_RE.search(pane):
        return "resume_mode_choice"
    if _OAUTH_RE.search(pane):
        return "oauth_pending"
    if _PROMPT_RE.search(pane):
        return "permission_prompt"
    # Busy MUST be checked before the ready_* states: a working claude still
    # shows the "Remote Control active" footer chip, so _RC_ACTIVE_RE would
    # otherwise mislabel a busy session as ready_with_remote_control.
    if _BUSY_RE.search(pane):
        return "busy"
    if _RC_ACTIVE_RE.search(pane):
        return "ready_with_remote_control"
    if _RC_HINT_RE.search(pane):
        return "ready_no_remote_control"
    # Idle at a prompt but remote-control state not visible in the pane text:
    # either a freshly-launched session (footer "? for shortcuts", no hostname
    # banner) or a hostname-bannered prompt. ensure_ready will run /remote-control.
    if _SHORTCUTS_RE.search(pane) or (_HOSTNAME_BANNER_RE.search(pane) and "❯" in pane):
        return "ready_unknown_remote_control"
    if _WELCOME_RE.search(pane):
        return "starting"
    return "unknown"


def remote_control_active(pane: str) -> bool:
    """Whether remote-control is on — independent of busy/ready. The footer chip
    'Remote Control active' (or body text '/remote-control is active') persists
    while claude works, so this stays accurate even when the label is 'busy'."""
    return bool(_RC_ACTIVE_RE.search(pane))


def parse_session_url(pane: str) -> Optional[str]:
    matches = _SESSION_URL_RE.findall(pane)
    if not matches:
        return None
    # Return full URL of last occurrence
    last = matches[-1]
    return f"https://claude.ai/code/{last}"


def parse_permission_prompt(pane: str) -> PromptInfo:
    """When a permission prompt is visible, extract the type, subject, danger level, options."""
    if not _PROMPT_RE.search(pane):
        return PromptInfo(active=False)

    # Find the prompt anchor (English or French) and look at the preceding context
    for anchor in ("Do you want to proceed", "Toujours autoriser", "Autoriser Claude"):
        idx = pane.rfind(anchor)
        if idx != -1:
            break
    window = pane[max(0, idx - 2000):idx + 200]

    action_type: ActionType = "Unknown"
    subject: Optional[str] = None

    # Try each action pattern
    for name, pat in _ACTION_PATTERNS:
        m = pat.search(window)
        if m:
            action_type = name  # type: ignore[assignment]
            try:
                subject = m.group(1).strip()
            except IndexError:
                subject = None
            break

    # Fallback for inline Bash(cmd)
    if action_type == "Unknown":
        m = _BASH_INLINE_RE.search(window)
        if m:
            action_type = "Bash"
            subject = m.group(1).strip()

    # Detect options from the prompt menu
    options = []
    full = window + pane[idx:idx + 200]
    if any(s in full for s in ("Yes, and", "don't ask again", "Toujours autoriser", "allow")):
        options = ["accept_once", "accept_all", "reject"]
    else:
        options = ["accept_once", "reject"]

    danger = _compute_danger(action_type, subject or "", window)

    return PromptInfo(
        active=True,
        type=action_type,
        subject=subject,
        danger=danger,
        options=options,
    )


def _compute_danger(action_type: ActionType, subject: str, window: str) -> DangerLevel:
    """Heuristic to color-code the prompt."""
    # Always green: pure reads
    if action_type in ("Read", "WebSearch"):
        return "green"

    # Red: dangerous Bash patterns
    if action_type == "Bash" and (_DANGER_RE.search(subject) or _DANGER_RE.search(window)):
        return "red"

    # Orange: regular Bash (could be anything)
    if action_type == "Bash":
        if _SUSPICIOUS_RE.search(subject) or _SUSPICIOUS_RE.search(window):
            return "orange"
        return "orange"

    # Yellow: edits to "safe" paths, MCP tools, WebFetch.
    # Derives from $HOME so this also works for non-root installs (cf. Pop's audit
    # 2026-06-14: the old /root/* literal classified darkbow_'s legit edits as
    # "orange" because nothing matched).
    import os as _os
    home = _os.path.expanduser("~")
    safe_paths = (
        "/tmp/",
        f"{home}/skills/",
        f"{home}/.claude-fleet-starter/",
        f"{home}/.claude/projects/",
        f"{home}/.config/",
    )
    if action_type in ("Edit", "Write", "NotebookEdit") and subject:
        if any(subject.startswith(p) for p in safe_paths):
            return "yellow"
        return "orange"

    if action_type in ("WebFetch", "MCP", "Agent"):
        return "yellow"

    # Default fallback
    return "orange"
