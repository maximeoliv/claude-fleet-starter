#!/usr/bin/env python3
"""Shared library for tailnet-messaging — frontmatter parsing, transfer model, inbox/archive.

A "transfer" is one message (.md with YAML frontmatter) + 0..N attachments, treated as a unit.
The frontmatter `attachments:` list links the message to its files.

Layout on each machine:
  ~/inbox/<transfer-id>/      — received transfers not yet processed
       message.md
       <attachment files>
  ~/taildrops-lus/<transfer-id>/  — archived (processed) transfers

Unread count = number of directories in ~/inbox/.
"""
from __future__ import annotations

import os
import re
import shutil
from datetime import datetime
from pathlib import Path

HOME = Path(os.path.expanduser("~"))
INBOX = HOME / "inbox"
ARCHIVE = HOME / "taildrops-lus"
STAGING = HOME / ".msg-staging"


def session_inbox(session: str) -> Path:
    return INBOX / "sessions" / session


def session_archive(session: str) -> Path:
    return ARCHIVE / "sessions" / session

# Files in HOME that are never taildrop messages
_NEVER_MESSAGE = {"CLAUDE.md"}


def ensure_dirs() -> None:
    for d in (INBOX, ARCHIVE, STAGING):
        d.mkdir(parents=True, exist_ok=True)


# ────────────────────────────────────────────────────────────────────────────
# Frontmatter parsing
# ────────────────────────────────────────────────────────────────────────────

_FM_BLOCK_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def parse_frontmatter(md_text: str) -> dict:
    """Parse a minimal YAML frontmatter block. Returns {} if none.

    Supports: simple `key: value` lines, and a list form:
        attachments:
          - file1
          - file2
    """
    m = _FM_BLOCK_RE.match(md_text)
    if not m:
        return {}
    block = m.group(1)
    result: dict = {}
    current_list_key: str | None = None
    for raw in block.split("\n"):
        line = raw.rstrip()
        if not line.strip():
            continue
        # List item
        li = re.match(r"\s+-\s+(.+)$", line)
        if li and current_list_key:
            result.setdefault(current_list_key, []).append(li.group(1).strip())
            continue
        # key: value
        kv = re.match(r"([A-Za-z_][\w-]*):\s*(.*)$", line)
        if kv:
            key, val = kv.group(1).strip(), kv.group(2).strip()
            if val == "":
                # Could be the start of a list
                current_list_key = key
                result.setdefault(key, [])
            else:
                current_list_key = None
                result[key] = val
    return result


def build_frontmatter(fields: dict) -> str:
    """Build a frontmatter block from a dict. `attachments` rendered as a list."""
    lines = ["---"]
    for key, val in fields.items():
        if val is None or val == "":
            continue
        if isinstance(val, list):
            if not val:
                continue
            lines.append(f"{key}:")
            for item in val:
                lines.append(f"  - {item}")
        else:
            lines.append(f"{key}: {val}")
    lines.append("---")
    return "\n".join(lines) + "\n"


# ────────────────────────────────────────────────────────────────────────────
# Transfer model
# ────────────────────────────────────────────────────────────────────────────

def slugify(text: str, maxlen: int = 32) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", (text or "").lower()).strip("-")
    return s[:maxlen] or "msg"


def make_transfer_id(sender: str, subject: str) -> str:
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"{ts}_{slugify(sender or 'unknown', 16)}_{slugify(subject, 32)}"


def list_transfers(directory: Path) -> list[dict]:
    """List transfers in a directory (inbox or archive). Each transfer is a subdir.

    Returns: [{id, path, message_file, sender, subject, priority, attachments, received_at}]
    """
    if not directory.exists():
        return []
    out = []
    for tdir in sorted(directory.iterdir(), reverse=True):
        if not tdir.is_dir():
            continue
        # Skip the sessions/ container — it holds per-session sub-inboxes,
        # not a transfer itself. Listed via --session or list_session_transfers().
        if tdir.name == "sessions":
            continue
        msg_file = None
        for cand in tdir.iterdir():
            if cand.suffix == ".md":
                msg_file = cand
                break
        info: dict = {
            "id": tdir.name,
            "path": str(tdir),
            "message_file": str(msg_file) if msg_file else None,
            "sender": None,
            "subject": None,
            "priority": None,
            "for_human_only": False,
            "attachments": [],
            "received_at": datetime.fromtimestamp(tdir.stat().st_mtime).isoformat(),
        }
        if msg_file:
            try:
                fm = parse_frontmatter(msg_file.read_text(errors="replace"))
                info["sender"] = fm.get("from")
                info["subject"] = fm.get("subject")
                info["priority"] = fm.get("priority")
                info["for_human_only"] = (fm.get("for_human_only", "").lower() == "yes")
                atts = fm.get("attachments") or []
                info["attachments"] = atts if isinstance(atts, list) else [atts]
            except Exception:
                pass
        # List actual files present (besides the .md)
        info["files"] = [f.name for f in tdir.iterdir() if f.is_file()]
        out.append(info)
    return out


def archive_transfer(transfer_id: str) -> bool:
    """Move a transfer from inbox to archive."""
    src = INBOX / transfer_id
    if not src.is_dir():
        return False
    dst = ARCHIVE / transfer_id
    if dst.exists():
        shutil.rmtree(dst)
    shutil.move(str(src), str(dst))
    return True


def inbox_count() -> int:
    if not INBOX.exists():
        return 0
    return sum(1 for d in INBOX.iterdir() if d.is_dir() and d.name != "sessions")


def list_session_transfers(session: str) -> list[dict]:
    return list_transfers(session_inbox(session))


def session_inbox_count(session: str) -> int:
    d = session_inbox(session)
    if not d.exists():
        return 0
    return sum(1 for x in d.iterdir() if x.is_dir())


def all_inbox_count() -> int:
    """Count all unread: machine-wide + all sessions."""
    total = inbox_count()
    sessions_dir = INBOX / "sessions"
    if sessions_dir.exists():
        for sdir in sessions_dir.iterdir():
            if sdir.is_dir():
                total += sum(1 for x in sdir.iterdir() if x.is_dir())
    return total


def archive_session_transfer(session: str, transfer_id: str) -> bool:
    """Move a session transfer from session inbox to session archive."""
    src = session_inbox(session) / transfer_id
    if not src.is_dir():
        return False
    dst = session_archive(session) / transfer_id
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        shutil.rmtree(dst)
    shutil.move(str(src), str(dst))
    return True


def archive_transfer_anywhere(transfer_id: str) -> bool:
    """Archive a transfer from machine inbox or any session inbox."""
    if archive_transfer(transfer_id):
        return True
    sessions_dir = INBOX / "sessions"
    if sessions_dir.exists():
        for sdir in sessions_dir.iterdir():
            if sdir.is_dir() and (sdir / transfer_id).is_dir():
                return archive_session_transfer(sdir.name, transfer_id)
    return False


def get_transfer_content_anywhere(transfer_id: str) -> dict | None:
    """Look up a transfer in machine inbox/archive AND all session inboxes/archives."""
    result = get_transfer_content(transfer_id)
    if result:
        return result
    for base in (INBOX, ARCHIVE):
        sessions_dir = base / "sessions"
        if not sessions_dir.exists():
            continue
        for sdir in sessions_dir.iterdir():
            if not sdir.is_dir():
                continue
            tdir = sdir / transfer_id
            if not tdir.is_dir():
                continue
            msg_file = next((f for f in tdir.iterdir() if f.suffix == ".md"), None)
            message_text = ""
            fm: dict = {}
            if msg_file:
                try:
                    raw = msg_file.read_text(errors="replace")
                    fm = parse_frontmatter(raw)
                    message_text = raw
                except Exception:
                    pass
            attachments = [
                {"name": f.name, "size": f.stat().st_size}
                for f in sorted(tdir.iterdir())
                if f.is_file() and f.suffix != ".md"
            ]
            return {
                "id": transfer_id,
                "location": "inbox" if base is INBOX else "archive",
                "session": sdir.name,
                "sender": fm.get("from"),
                "subject": fm.get("subject"),
                "priority": fm.get("priority"),
                "message_filename": msg_file.name if msg_file else None,
                "message_text": message_text,
                "attachments": attachments,
            }
    return None


def get_transfer_content(transfer_id: str) -> dict | None:
    """Return the full content of a transfer (message text + attachment names).

    Looks in inbox first, then archive. Returns None if not found.
    """
    for base in (INBOX, ARCHIVE):
        tdir = base / transfer_id
        if not tdir.is_dir():
            continue
        msg_file = None
        for cand in tdir.iterdir():
            if cand.suffix == ".md":
                msg_file = cand
                break
        message_text = ""
        fm: dict = {}
        if msg_file:
            try:
                raw = msg_file.read_text(errors="replace")
                fm = parse_frontmatter(raw)
                message_text = raw
            except Exception:
                pass
        attachments = [
            {"name": f.name, "size": f.stat().st_size}
            for f in sorted(tdir.iterdir())
            if f.is_file() and f.suffix != ".md"
        ]
        return {
            "id": transfer_id,
            "location": "inbox" if base is INBOX else "archive",
            "sender": fm.get("from"),
            "subject": fm.get("subject"),
            "priority": fm.get("priority"),
            "message_filename": msg_file.name if msg_file else None,
            "message_text": message_text,
            "attachments": attachments,
        }
    return None
