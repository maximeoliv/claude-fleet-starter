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
# Phase B (2026-06-20) — sent archive: every successful msg-send leaves a copy
# here so the machine remembers what it has sent (and the receipts / reply
# tracker can match incoming events to outbound IDs).
SENT = HOME / "taildrops-envoyes"
# Phase A — receipts (delivered/read events from receivers) are routed to a
# dedicated subdir of the archive so they DON'T inflate the unread counter.
RECEIPTS = ARCHIVE / "receipts"
# Phase C — per-sent-id status tracker (delivered | read | replied | closed).
# One file per outbound transfer: <id>.json with {status, updated_at, replies: [...]}
SENT_STATUS = HOME / ".msg-sent-status"


def session_inbox(session: str) -> Path:
    return INBOX / "sessions" / session


def session_archive(session: str) -> Path:
    return ARCHIVE / "sessions" / session

# Files in HOME that are never taildrop messages
_NEVER_MESSAGE = {"CLAUDE.md"}


def ensure_dirs() -> None:
    for d in (INBOX, ARCHIVE, STAGING, SENT, RECEIPTS, SENT_STATUS):
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
    """Look up a transfer in machine inbox/archive AND all session inboxes/archives.
    Also checks SENT (taildrops-envoyes) and RECEIPTS (taildrops-lus/receipts/).
    """
    result = get_transfer_content(transfer_id)
    if result:
        return result
    # Sent archive (Phase B 2026-06-20)
    sent_content = get_sent_content(transfer_id)
    if sent_content:
        return sent_content
    # Receipts (Phase A 2026-06-20)
    rdir = RECEIPTS / transfer_id
    if rdir.is_dir():
        msg_file = next((f for f in rdir.iterdir() if f.suffix == ".md"), None)
        fm: dict = {}
        message_text = ""
        if msg_file:
            try:
                raw = msg_file.read_text(errors="replace")
                fm = parse_frontmatter(raw)
                message_text = raw
            except Exception:
                pass
        return {
            "id": transfer_id,
            "location": "receipt",
            "sender": fm.get("from"),
            "subject": fm.get("subject"),
            "priority": fm.get("priority"),
            "kind": fm.get("kind"),
            "message_filename": msg_file.name if msg_file else None,
            "message_text": message_text,
            "attachments": [],
        }
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


# ────────────────────────────────────────────────────────────────────────────
# Phase B — sent archive
# ────────────────────────────────────────────────────────────────────────────

def archive_sent(transfer_id: str, message_path: Path, attachment_paths: list[Path],
                 dest: str | None = None) -> Path:
    """Persist a successful outbound message + attachments to ~/taildrops-envoyes/<id>/.

    The on-disk shape mirrors ~/inbox/<id>/ exactly so the same list_transfers()
    / get_transfer_content() helpers work, just pointed at SENT instead.
    Returns the directory created.
    """
    ensure_dirs()
    tdir = SENT / transfer_id
    tdir.mkdir(parents=True, exist_ok=True)
    # Copy message
    shutil.copy2(str(message_path), str(tdir / message_path.name))
    # Copy attachments (if any)
    for ap in attachment_paths:
        shutil.copy2(str(ap), str(tdir / ap.name))
    # Persist a tiny meta file so we know the intended destination (may have
    # been "host:session" or a UUID — the message frontmatter only has "to" as
    # the raw string).
    if dest:
        (tdir / ".dest").write_text(dest)
    return tdir


def list_sent() -> list[dict]:
    """List archived sent transfers (mirrors list_transfers for SENT)."""
    return list_transfers(SENT)


def get_sent_content(transfer_id: str) -> dict | None:
    """Read back a sent transfer's content (message text + attachments). Returns None if absent."""
    tdir = SENT / transfer_id
    if not tdir.is_dir():
        return None
    msg_file = next((f for f in tdir.iterdir() if f.suffix == ".md"), None)
    fm: dict = {}
    message_text = ""
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
        if f.is_file() and f.suffix != ".md" and not f.name.startswith(".")
    ]
    dest_file = tdir / ".dest"
    dest = dest_file.read_text().strip() if dest_file.exists() else fm.get("to")
    return {
        "id": transfer_id,
        "location": "sent",
        "dest": dest,
        "to": fm.get("to"),
        "from": fm.get("from"),
        "subject": fm.get("subject"),
        "priority": fm.get("priority"),
        "in_reply_to": fm.get("in_reply_to"),
        "kind": fm.get("kind"),
        "message_filename": msg_file.name if msg_file else None,
        "message_text": message_text,
        "attachments": attachments,
    }


# ────────────────────────────────────────────────────────────────────────────
# Phase A — receipts
# ────────────────────────────────────────────────────────────────────────────

def is_receipt(fm: dict) -> bool:
    """Detect a kind:receipt-* frontmatter — those bypass the unread counter."""
    kind = (fm.get("kind") or "").strip().lower()
    return kind.startswith("receipt")


def stash_receipt(transfer_id: str, message_path: Path) -> Path:
    """Route an incoming receipt to ~/taildrops-lus/receipts/<id>/ (out of inbox)."""
    ensure_dirs()
    dst = RECEIPTS / transfer_id
    dst.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(message_path), str(dst / message_path.name))
    return dst


def list_receipts(limit: int | None = None) -> list[dict]:
    """List receipts received from peers."""
    out = list_transfers(RECEIPTS)
    return out[:limit] if limit else out


# ────────────────────────────────────────────────────────────────────────────
# Phase C — sent status tracker
# ────────────────────────────────────────────────────────────────────────────

def _status_file(transfer_id: str) -> Path:
    return SENT_STATUS / f"{transfer_id}.json"


def init_sent_status(transfer_id: str, dest: str | None = None) -> None:
    """Create the initial status record for an outbound message (status=delivered)."""
    import json as _json
    ensure_dirs()
    f = _status_file(transfer_id)
    f.write_text(_json.dumps({
        "id": transfer_id,
        "dest": dest,
        "status": "delivered",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "replies": [],
        "receipts": [],
    }, indent=2))


def get_sent_status(transfer_id: str) -> dict | None:
    import json as _json
    f = _status_file(transfer_id)
    if not f.exists():
        return None
    try:
        return _json.loads(f.read_text())
    except Exception:
        return None


def update_sent_status(transfer_id: str, **kwargs) -> bool:
    """Merge fields into an existing status record. Special keys append:
    `add_reply=<incoming_id>` → appends to replies[]
    `add_receipt=<receipt_id>` → appends to receipts[]
    `set_status=read|replied|closed` → bumps status (no downgrade)
    """
    import json as _json
    f = _status_file(transfer_id)
    if not f.exists():
        return False
    try:
        rec = _json.loads(f.read_text())
    except Exception:
        return False

    rank = {"delivered": 0, "read": 1, "replied": 2, "closed": 3}
    if kwargs.get("add_reply"):
        if kwargs["add_reply"] not in rec["replies"]:
            rec["replies"].append(kwargs["add_reply"])
    if kwargs.get("add_receipt"):
        if kwargs["add_receipt"] not in rec["receipts"]:
            rec["receipts"].append(kwargs["add_receipt"])
    new_status = kwargs.get("set_status")
    if new_status and rank.get(new_status, -1) > rank.get(rec.get("status", "delivered"), 0):
        rec["status"] = new_status
    rec["updated_at"] = datetime.now().isoformat(timespec="seconds")
    f.write_text(_json.dumps(rec, indent=2))
    return True


def list_sent_status(limit: int | None = None) -> list[dict]:
    """Return the status records, newest first."""
    if not SENT_STATUS.exists():
        return []
    import json as _json
    out = []
    for f in sorted(SENT_STATUS.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            out.append(_json.loads(f.read_text()))
        except Exception:
            continue
    return out[:limit] if limit else out


# ────────────────────────────────────────────────────────────────────────────
# Phase F — thread reconstruction
# ────────────────────────────────────────────────────────────────────────────

def _all_messages_with_fm() -> list[dict]:
    """Return every message known to this machine (inbox + archive + sent + receipts)
    in chronological order, with frontmatter parsed.
    """
    out = []
    for src_dir, source in [
        (INBOX, "inbox"),
        (ARCHIVE, "archive"),
        (SENT, "sent"),
        (RECEIPTS, "receipt"),
    ]:
        if not src_dir.exists():
            continue
        for tdir in src_dir.iterdir():
            if not tdir.is_dir() or tdir.name in ("sessions", "receipts"):
                continue
            msg_file = next((f for f in tdir.iterdir() if f.suffix == ".md"), None)
            if not msg_file:
                continue
            try:
                raw = msg_file.read_text(errors="replace")
                fm = parse_frontmatter(raw)
            except Exception:
                continue
            out.append({
                "id": tdir.name,
                "source": source,
                "from": fm.get("from"),
                "to": fm.get("to"),
                "subject": fm.get("subject"),
                "date": fm.get("date"),
                "priority": fm.get("priority"),
                "kind": fm.get("kind"),
                "in_reply_to": fm.get("in_reply_to"),
                "ts": tdir.stat().st_mtime,
            })
    out.sort(key=lambda m: m["ts"])
    return out


def reconstruct_thread(transfer_id: str) -> list[dict]:
    """Build the full thread rooted at the message that doesn't reply to anything
    in the chain containing <transfer_id>. Includes sent, received, archived, receipts.
    """
    all_msgs = _all_messages_with_fm()
    by_id = {m["id"]: m for m in all_msgs}
    if transfer_id not in by_id:
        return []
    # Walk backwards to the root
    cursor = transfer_id
    while True:
        parent = by_id[cursor].get("in_reply_to")
        if parent and parent in by_id:
            cursor = parent
        else:
            break
    root_id = cursor
    # Now collect all messages that have root_id as an ancestor (or are root_id itself)
    def ancestors(mid: str) -> list[str]:
        chain = [mid]
        cur = mid
        while True:
            nxt = by_id.get(cur, {}).get("in_reply_to")
            if not nxt or nxt not in by_id:
                break
            chain.append(nxt)
            cur = nxt
        return chain
    thread = [m for m in all_msgs if root_id in ancestors(m["id"])]
    return thread
