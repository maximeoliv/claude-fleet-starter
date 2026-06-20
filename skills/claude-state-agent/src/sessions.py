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
                     (convention: "main-host" session = the machine-wide one)
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

    def _proc_cmdline(pid: str) -> str:
        try:
            with open(f"/proc/{pid}/cmdline", "rb") as f:
                return f.read().replace(b"\x00", b" ").decode(errors="replace").strip()
        except Exception:
            return ""

    def _is_claude_cmd(cmdline: str) -> bool:
        # match the claude binary, not arbitrary processes that contain "claude"
        # in a path arg (e.g. node MCP servers under /root/.claude/...).
        low = cmdline.lower()
        first = (cmdline.split() or [""])[0].lower()
        return (
            first.endswith("/claude") or first == "claude"
            or low.startswith("claude ") or low == "claude"
            or "/.local/bin/claude" in low
        )

    for pane_pid in pane_pids:
        pane_pid = pane_pid.strip()
        # 1. The pane process itself may BE claude (e.g. when launched via
        #    `bash -c '... && claude ...'` where bash exec's into claude, the
        #    claude process replaces the pane shell). In that case its children
        #    are MCP servers, not claude — so check the pane pid first.
        pane_cmd = _proc_cmdline(pane_pid)
        if _is_claude_cmd(pane_cmd):
            cwd = Path(f"/proc/{pane_pid}/cwd").resolve().as_posix() if Path(f"/proc/{pane_pid}/cwd").exists() else "/root"
            return {"pid": pane_pid, "cwd": cwd, "cmdline": pane_cmd}

        # 2. Otherwise walk the FULL descendant tree (BFS), not just direct
        #    children — claude may be a grandchild (pane->bash->claude).
        try:
            queue = [pane_pid]
            seen = set()
            while queue:
                cur = queue.pop(0)
                if cur in seen:
                    continue
                seen.add(cur)
                r = subprocess.run(
                    ["pgrep", "-P", cur],
                    capture_output=True, text=True, timeout=3,
                )
                for child_pid in r.stdout.split():
                    cmdline = _proc_cmdline(child_pid)
                    if _is_claude_cmd(cmdline):
                        cwd = Path(f"/proc/{child_pid}/cwd").resolve().as_posix() if Path(f"/proc/{child_pid}/cwd").exists() else "/root"
                        return {"pid": child_pid, "cwd": cwd, "cmdline": cmdline}
                    queue.append(child_pid)
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
    """Load ~/.claude/sessions.json — per-session metadata used to enrich
    /sessions/discover for the fleet directory (see central-aggregator
    /fleet/sessions aggregator).

    Format:
      {
        "tmux_session_name": {
          "description": "What this session is for",
          "name": "optional-override-slug",
          "parent": "main-host:claude",           # n+1 in fleet hierarchy
                                                  # (use the `<host>:<tmux>` form,
                                                  #  null = root of fleet)
          "scope": "Plugin MyShadow (Paper)",     # short human-readable scope
          "role": "machine-wide-root|machine-wide|project-dedicated|fork|ephemeral"
        }
      }

    All fields beyond `description` and `name` are optional; sensible defaults
    are computed in collect_sessions() (parent = host's machine-wide for child
    sessions, role inferred from is_machine_wide + forked_from).
    """
    if not SESSIONS_OVERRIDE.exists():
        return {}
    try:
        return json.loads(SESSIONS_OVERRIDE.read_text())
    except Exception:
        return {}


_HOSTNAME_ROOT = "main-host"  # coordinator of the fleet — parent=null for its main session.
                              # NOTE: change this to your own coordinator hostname (the machine
                              # running the central-aggregator). Every other machine-wide session
                              # will be declared as a child of "<root>:claude".


def _default_parent(host: str, tmux_name: str, cwd: str, is_machine_wide: bool,
                    same_host_sessions: list[dict] | None = None) -> str | None:
    """Default n+1 in the fleet hierarchy when the override file doesn't specify.

    For non-machine-wide sessions, walk all other same-host sessions and pick the
    one whose cwd is the *longest proper prefix* of this session's cwd. That gives
    us arbitrary nesting depth (e.g. /root/projets/paperclip/feature-X reports to
    the session at /root/projets/paperclip if it exists, otherwise to
    /root/projets if it exists, otherwise to the machine-wide).

    If no same-host parent matches → fall back to the machine-wide of this host.
    Cross-host parents (e.g. agents:opencode-bot → panels:paperclip) require an
    explicit `parent` override in ~/.claude/sessions.json — they can't be
    inferred from cwd because the cwd of "agents" lives on a different machine.
    """
    if is_machine_wide:
        if host == _HOSTNAME_ROOT:
            return None  # root of the fleet
        return f"{_HOSTNAME_ROOT}:claude"

    # Find the same-host session with the longest cwd that is a *proper* prefix
    # of ours (and isn't ourselves).
    best = None
    best_len = -1
    for s in (same_host_sessions or []):
        s_cwd = s.get("cwd") or ""
        if not s_cwd or s_cwd == cwd:
            continue
        if cwd == s_cwd or cwd.startswith(s_cwd.rstrip("/") + "/"):
            if len(s_cwd) > best_len:
                best = s
                best_len = len(s_cwd)
    if best:
        return f"{host}:{best['tmux_session']}"
    return f"{host}:claude"  # fallback: machine-wide


def _default_role(host: str, is_machine_wide: bool, forked_from: str | None) -> str:
    """Default role when the override file doesn't specify."""
    if is_machine_wide:
        return "machine-wide-root" if host == _HOSTNAME_ROOT else "machine-wide"
    if forked_from:
        return "fork"
    return "project-dedicated"


def _greedy_assign_jsonls(sessions_with_jsonls: list[dict]) -> None:
    """Filet de sécurité pour le bug "même cwd = même jsonl" (panels 21/06).

    Quand plusieurs sessions tmux partagent un cwd (project dir Claude
    Code identique), find_active_jsonl(cwd) renvoie le jsonl le plus
    récemment écrit pour TOUTES — donc le `session_uuid` est faux pour
    toutes sauf une. La vraie fix architecturale est la convention
    "1 session = 1 cwd dédié sous $HOME/projets/", mais en attendant que
    toutes les machines migrent, on apparie greedy par activité.

    Algorithme :
    1. Groupe les sessions par project_slug (= cwd-dérivé).
    2. Dans chaque groupe, trie les sessions par `tmux_session_activity`
       DESC (la plus récemment active en haut).
    3. Liste les jsonl du project dir, triés par mtime DESC.
    4. Apparie 1-1 dans l'ordre. La session avec l'activité la plus
       récente prend le jsonl avec le mtime le plus récent.

    Modifie chaque dict in-place: `session_uuid`, `forked_from`,
    `description` sont ré-extraits du jsonl assigné.
    """
    from collections import defaultdict
    groups: dict[str, list[dict]] = defaultdict(list)
    for s in sessions_with_jsonls:
        if s.get("_cwd") and s.get("_project_dir"):
            groups[s["_project_dir"]].append(s)

    for project_dir, sessions in groups.items():
        if len(sessions) <= 1:
            continue  # rien à désambiguïser
        try:
            jsonls = sorted(
                Path(project_dir).glob("*.jsonl"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
        except Exception:
            continue
        # Sort sessions by tmux activity desc — fallback to tmux name for stability.
        sessions.sort(key=lambda s: (s.get("_tmux_activity") or "0", s["tmux_session"]), reverse=True)
        for i, sess in enumerate(sessions):
            if i >= len(jsonls):
                break
            jsonl = jsonls[i]
            sess["session_uuid"] = jsonl.stem
            sess["forked_from"] = detect_fork_parent(jsonl)
            if not sess.get("description"):
                sess["description"] = extract_first_user_prompt(jsonl)


def collect_sessions() -> list[dict[str, Any]]:
    """Discover all Claude Code sessions running on this machine."""
    overrides = load_overrides()
    tmux_meta = {t["name"]: t for t in list_tmux_sessions()}

    # First pass: collect all raw session data (without parent resolution)
    raw_sessions: list[dict[str, Any]] = []
    for tmux_name, tmux_info in tmux_meta.items():
        proc = _find_claude_process_for_tmux(tmux_name)
        if not proc:
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
        is_machine_wide = (name == _HOSTNAME or tmux_name == "claude")

        raw_sessions.append({
            "id": f"{_HOSTNAME}:{tmux_name}",
            "tmux_session": tmux_name,
            "name": ov.get("name") or name,
            "description": description,
            "session_uuid": session_uuid,
            "cwd": cwd,
            "project_slug": cwd_to_slug(cwd),
            "remote_control": parsed.get("remote_control"),
            "is_machine_wide": is_machine_wide,
            "forked_from": forked_from,
            "pid": proc["pid"],
            "host": _HOSTNAME,
            "scope": ov.get("scope", ""),
            # Internal fields used by greedy disambiguation, dropped before return
            "_override_parent": ov.get("parent", None),
            "_override_role": ov.get("role", None),
            "_cwd": cwd,
            "_project_dir": str(CLAUDE_PROJECTS / cwd_to_slug(cwd)) if cwd else None,
            "_tmux_activity": tmux_info.get("attached", "0"),
        })

    # Filet de sécurité: ré-apparie jsonls quand plusieurs sessions partagent un cwd
    _greedy_assign_jsonls(raw_sessions)

    # Second pass: resolve parent + role with full session list available
    out: list[dict[str, Any]] = []
    for s in raw_sessions:
        is_machine_wide = s["is_machine_wide"]
        override_parent = s.pop("_override_parent")
        override_role = s.pop("_override_role")
        cwd = s.pop("_cwd")
        s.pop("_project_dir", None)
        s.pop("_tmux_activity", None)

        # Parent — override wins, otherwise compute via cwd hierarchy
        parent = (override_parent if override_parent is not None
                  else _default_parent(_HOSTNAME, s["tmux_session"], cwd,
                                        is_machine_wide, raw_sessions))
        role = (override_role if override_role is not None
                else _default_role(_HOSTNAME, is_machine_wide, s.get("forked_from")))

        s["parent"] = parent
        s["role"] = role
        out.append(s)

    return out
