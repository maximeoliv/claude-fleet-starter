"""Discover Claude Code sessions running on this machine.

A "session" here = a Claude Code process running inside a tmux session, paired
with its underlying .jsonl transcript in ~/.claude/projects/<slug>/.

For each session we surface:
  - tmux_session  : tmux session name (e.g. "claude", "deck-ia", "mcp-vapi")
  - name          : the --name slug passed to claude (falls back to tmux name)
  - description   : human-readable summary
                    1. user-provided in ~/.claude/sessions.json (override)
                    2. otherwise first user prompt of the active jsonl
                    3. otherwise empty
  - session_uuid  : the active session UUID (newest .jsonl matching the cwd)
  - cwd           : working directory of the claude process
  - project_slug  : ~/.claude/projects/<slug>/
  - remote_control: the RC alias if active
  - is_machine_wide: True if this session is the one named after the hostname
                     (convention: "byh-dell1" session = the machine-wide one)
  - forked_from   : parent session UUID if this jsonl was forked from another
                    (heuristic: shared early UUIDs with another jsonl)
"""
from __future__ import annotations

import json
import os
import re
import socket
import subprocess
from pathlib import Path
from typing import Any

HOME = Path(os.path.expanduser("~"))
CLAUDE_PROJECTS = HOME / ".claude" / "projects"
SESSIONS_OVERRIDE = HOME / ".claude" / "sessions.json"


def _hostname() -> str:
    return socket.gethostname().lower()


_HOSTNAME = _hostname()


def list_tmux_sessions() -> list[dict[str, str]]:
    """Return all tmux sessions on this machine."""
    try:
        r = subprocess.run(
            ["tmux", "list-sessions", "-F",
             "#{session_name}|#{session_created}|#{session_attached}"],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode != 0:
            return []
    except Exception:
        return []
    out = []
    for line in r.stdout.strip().splitlines():
        parts = line.split("|")
        if len(parts) >= 3:
            out.append({"name": parts[0], "created": parts[1], "attached": parts[2]})
    return out


def _read_pane_cmd(tmux_session: str) -> str:
    """Get the command running in the tmux session's first pane."""
    try:
        r = subprocess.run(
            ["tmux", "list-panes", "-t", tmux_session, "-F", "#{pane_current_command}|#{pane_pid}"],
            capture_output=True, text=True, timeout=5,
        )
        return r.stdout.strip().splitlines()[0] if r.returncode == 0 else ""
    except Exception:
        return ""


def _find_claude_process_for_tmux(tmux_session: str) -> dict[str, Any] | None:
    """Find the claude process running inside a tmux session.

    Returns {pid, cwd, cmdline_name} or None if no claude is running there.
    """
    try:
        r = subprocess.run(
            ["tmux", "list-panes", "-t", tmux_session, "-F", "#{pane_pid}"],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode != 0:
            return None
        pane_pids = r.stdout.strip().splitlines()
    except Exception:
        return None

    for pane_pid in pane_pids:
        # Walk children of the pane shell to find a claude process
        try:
            r = subprocess.run(
                ["pgrep", "-P", pane_pid.strip(), "-a"],
                capture_output=True, text=True, timeout=3,
            )
            for line in r.stdout.splitlines():
                if "claude" in line.lower():
                    pid = line.split()[0]
                    cmdline = " ".join(line.split()[1:])
                    cwd = Path(f"/proc/{pid}/cwd").resolve().as_posix() if Path(f"/proc/{pid}/cwd").exists() else "/root"
                    return {"pid": pid, "cwd": cwd, "cmdline": cmdline}
        except Exception:
            continue
    return None


_NAME_RE = re.compile(r"--name[= ]([^\s]+)")
_RC_RE = re.compile(r"--remote-control[= ]([^\s]+)")


def parse_cmdline(cmdline: str) -> dict[str, str]:
    """Extract --name and --remote-control args from a claude cmdline."""
    out: dict[str, str] = {}
    m = _NAME_RE.search(cmdline)
    if m:
        out["name"] = m.group(1).strip('"\'')
    m = _RC_RE.search(cmdline)
    if m:
        out["remote_control"] = m.group(1).strip('"\'')
    return out


def cwd_to_slug(cwd: str) -> str:
    """Convert a cwd path to the ~/.claude/projects/<slug>/ directory name."""
    # Standard convention: replace path separators with dashes, prefix with dash
    return "-" + cwd.replace("/", "-").lstrip("-")


def find_active_jsonl(cwd: str) -> Path | None:
    """Find the most recently modified .jsonl in the project dir for this cwd."""
    slug = cwd_to_slug(cwd)
    project_dir = CLAUDE_PROJECTS / slug
    if not project_dir.exists():
        return None
    jsonls = list(project_dir.glob("*.jsonl"))
    if not jsonls:
        return None
    return max(jsonls, key=lambda p: p.stat().st_mtime)


def extract_first_user_prompt(jsonl_path: Path, max_len: int = 100) -> str:
    """Extract the first real user prompt from a session jsonl.

    Skips system-reminders, command-stdout, attachments — only real user text.
    """
    try:
        with open(jsonl_path, encoding="utf-8", errors="replace") as f:
            for line in f:
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                if obj.get("type") != "user":
                    continue
                content = obj.get("message", {}).get("content")
                if isinstance(content, str):
                    txt = content
                elif isinstance(content, list):
                    txt = ""
                    for blk in content:
                        if isinstance(blk, dict) and blk.get("type") == "text":
                            txt = blk.get("text", "")
                            break
                else:
                    continue
                # Skip injected system content
                if not txt or txt.startswith("<"):
                    continue
                txt = " ".join(txt.split())
                return txt[:max_len] + ("..." if len(txt) > max_len else "")
    except Exception:
        pass
    return ""


def detect_fork_parent(jsonl_path: Path) -> str | None:
    """Detect if this jsonl was forked from another by checking early UUIDs.

    Heuristic: if the first message has parentUuid that's not present anywhere
    in this jsonl, it was forked. Look up which other jsonl in projects/ has
    that parentUuid — that's the source session.
    """
    try:
        with open(jsonl_path, encoding="utf-8", errors="replace") as f:
            uuids_in_this = set()
            first_parent = None
            for i, line in enumerate(f):
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                if "uuid" in obj:
                    uuids_in_this.add(obj["uuid"])
                if first_parent is None and obj.get("parentUuid"):
                    first_parent = obj["parentUuid"]
                if i > 5:
                    break
        if first_parent and first_parent not in uuids_in_this:
            # Find which other jsonl has this UUID
            project_dir = jsonl_path.parent
            for other in project_dir.glob("*.jsonl"):
                if other == jsonl_path:
                    continue
                try:
                    with open(other, encoding="utf-8", errors="replace") as f:
                        for line in f:
                            if first_parent in line:
                                return other.stem  # filename = session UUID
                except Exception:
                    continue
    except Exception:
        pass
    return None


def load_overrides() -> dict[str, dict[str, str]]:
    """Load ~/.claude/sessions.json which lets the user override descriptions/names.

    Format:
      {
        "tmux_session_name": {
          "description": "What this session is for",
          "name": "optional-override-slug"
        }
      }
    """
    if not SESSIONS_OVERRIDE.exists():
        return {}
    try:
        return json.loads(SESSIONS_OVERRIDE.read_text())
    except Exception:
        return {}


def collect_sessions() -> list[dict[str, Any]]:
    """Discover all Claude Code sessions running on this machine."""
    overrides = load_overrides()
    out: list[dict[str, Any]] = []

    for tmux in list_tmux_sessions():
        tmux_name = tmux["name"]
        proc = _find_claude_process_for_tmux(tmux_name)
        if not proc:
            # tmux session exists but no claude inside — skip
            continue

        parsed = parse_cmdline(proc["cmdline"])
        cwd = proc["cwd"]
        jsonl = find_active_jsonl(cwd)
        session_uuid = jsonl.stem if jsonl else None
        first_prompt = extract_first_user_prompt(jsonl) if jsonl else ""
        forked_from = detect_fork_parent(jsonl) if jsonl else None

        name = parsed.get("name") or tmux_name
        ov = overrides.get(tmux_name, {})
        description = ov.get("description") or first_prompt

        out.append({
            "tmux_session": tmux_name,
            "name": ov.get("name") or name,
            "description": description,
            "session_uuid": session_uuid,
            "cwd": cwd,
            "project_slug": cwd_to_slug(cwd),
            "remote_control": parsed.get("remote_control"),
            "is_machine_wide": (name == _HOSTNAME or tmux_name == "claude"),
            "forked_from": forked_from,
            "pid": proc["pid"],
            "host": _HOSTNAME,
        })
    return out
