"""claude-state-agent — local HTTP agent exposing this machine's claude state.

Runs on every fleet machine. A central aggregator (the dashboard you build for
your fleet) polls this agent over plain HTTP instead of SSH. Read-only endpoints
(`/health`, `/state`, `/sessions`) are open; everything that mutates state
(`/action`, `/claude/start`, `/sessions/{s}/inject`, `/telemetry`, …) requires
the `X-Fleet-Token` header (see `auth.py`).
"""
from __future__ import annotations

import logging
import re

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import actions
from .auth import accept_all_enabled, require_token
from .local_state import get_local_state
from .models import ActionRequest, InjectRequest, LocalState, SessionInfo

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("claude-state-agent")

app = FastAPI(title="claude-state-agent", version="1.1.0")

# CORS: localhost (any port) + tailnet CGNAT range (100.64.0.0/10) only.
# No wildcard. If you front this with a proxy on another origin, add it to
# CLAUDE_FLEET_EXTRA_ORIGINS (comma-separated) via the systemd unit.
import os as _os

_EXTRA = [o.strip() for o in _os.environ.get("CLAUDE_FLEET_EXTRA_ORIGINS", "").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://127.0.0.1", *_EXTRA],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1|100\.(6[4-9]|[7-9]\d|1[01]\d|12[0-7])\.\d+\.\d+)(:\d+)?$",
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["X-Fleet-Token", "Content-Type"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/state", response_model=LocalState)
async def state():
    """Full local state — claude status, prompt, pressure, transfers."""
    return get_local_state()


@app.post("/action", dependencies=[Depends(require_token)])
async def do_action(req: ActionRequest):
    if req.action == "accept_all" and not accept_all_enabled():
        raise HTTPException(
            status_code=403,
            detail=(
                "accept_all is disabled by default — set "
                "CLAUDE_FLEET_ALLOW_ACCEPT_ALL=1 in the systemd unit to enable. "
                "This action presses 'Yes, don't ask again' remotely without a human in the loop."
            ),
        )
    fn = {
        "accept_once": actions.accept_once,
        "accept_all": actions.accept_all,
        "reject": actions.reject,
        "esc": actions.send_esc,
        "compact_confirm": actions.send_compact,
        "clear_confirm": actions.send_clear,
    }.get(req.action)
    if not fn:
        raise HTTPException(status_code=400, detail=f"unknown action: {req.action}")
    return {"action": req.action, "ok": fn()}


@app.post("/claude/start", dependencies=[Depends(require_token)])
async def claude_start():
    """Start claude AND drive it to ready+remote-control (resume = full as-is, verified)."""
    import asyncio
    result = await asyncio.to_thread(actions.ensure_ready)
    return result


@app.post("/claude/ensure-ready", dependencies=[Depends(require_token)])
async def claude_ensure_ready():
    """Explicit: drive claude from any state to ready+remote-control."""
    import asyncio
    result = await asyncio.to_thread(actions.ensure_ready)
    return result


@app.post("/claude/stop", dependencies=[Depends(require_token)])
async def claude_stop():
    return {"ok": actions.claude_stop()}


@app.post("/claude/restart", dependencies=[Depends(require_token)])
async def claude_restart():
    return {"ok": actions.claude_restart()}


@app.post("/transfers/read", dependencies=[Depends(require_token)])
async def transfers_read(transfer_id: str | None = None):
    """Make the local claude read its taildrop transfer(s)."""
    return {"ok": actions.read_transfer(transfer_id), "transfer_id": transfer_id}


@app.post("/transfers/{transfer_id}/archive", dependencies=[Depends(require_token)])
async def transfer_archive(transfer_id: str):
    """Directly archive a transfer (mark-as-read)."""
    return {"ok": actions.archive_transfer(transfer_id), "transfer_id": transfer_id}


@app.get("/sessions", response_model=list[SessionInfo])
async def list_sessions():
    """List all tmux sessions with their claude state. (read-only, no token required)"""
    return actions.get_sessions_info()


@app.post("/sessions/{session}/inject", dependencies=[Depends(require_token)])
async def session_inject(session: str, req: InjectRequest):
    """Inject a prompt into a specific named tmux session."""
    ok = actions.inject_into_session(session, req.message)
    return {"ok": ok, "session": session}


@app.post("/sessions/{session}/start", dependencies=[Depends(require_token)])
async def session_start(session: str):
    """Create a tmux session and launch claude inside it."""
    ok = actions.start_named_session(session)
    return {"ok": ok, "session": session}


@app.post("/sessions/{session}/ensure-ready", dependencies=[Depends(require_token)])
async def session_ensure_ready(session: str):
    """Drive a specific tmux session to ready_with_remote_control."""
    import asyncio
    result = await asyncio.to_thread(actions.ensure_ready_session, session)
    return result


@app.get("/messaging/status")
async def messaging_status(limit: int = 50):
    """Return the messaging overview of this machine — outbound tracker, inbox count,
    receipts received, and an actionable "pending review" list.

    Surfaces what came out of the Phase A-F messaging refonte (2026-06-20). Does
    not require token (read-only), polled by the central-aggregator for the
    /fleet/messaging view.
    """
    import json
    import os
    from collections import Counter
    from pathlib import Path
    home = Path(os.path.expanduser("~"))
    sent_status_dir = home / ".msg-sent-status"
    receipts_dir = home / "taildrops-lus" / "receipts"
    inbox_dir = home / "inbox"

    records = []
    if sent_status_dir.exists():
        for f in sorted(sent_status_dir.glob("*.json"),
                        key=lambda p: p.stat().st_mtime, reverse=True)[:limit]:
            try:
                records.append(json.loads(f.read_text()))
            except Exception:
                continue

    status_counts = Counter(r.get("status", "delivered") for r in records)

    # Pending review = outbound where someone has replied but we haven't read THE REPLY
    # Heuristic: status=replied AND the most recent reply id is in our current inbox
    inbox_ids = set()
    if inbox_dir.exists():
        for d in inbox_dir.iterdir():
            if d.is_dir() and d.name != "sessions":
                inbox_ids.add(d.name)
    pending_review = [
        {"id": r["id"], "dest": r.get("dest"), "replies_pending": [
            rid for rid in r.get("replies", []) if rid in inbox_ids
        ]}
        for r in records
        if r.get("status") == "replied"
        and any(rid in inbox_ids for rid in r.get("replies", []))
    ]

    # Inbox unread count (matches msg_lib.inbox_count)
    inbox_unread = sum(1 for d in (inbox_dir.iterdir() if inbox_dir.exists() else [])
                       if d.is_dir() and d.name != "sessions")

    # Receipts count
    receipts_total = sum(1 for d in (receipts_dir.iterdir() if receipts_dir.exists() else [])
                        if d.is_dir())

    return {
        "host": __import__("socket").gethostname().lower(),
        "outbound": {
            "total": len(records),
            "status_breakdown": dict(status_counts),
            "pending_review": pending_review,
        },
        "inbox": {
            "unread": inbox_unread,
        },
        "receipts": {
            "total_received": receipts_total,
        },
    }


@app.get("/sessions/discover")
async def sessions_discover():
    """List all Claude Code sessions running on this machine — V2 multi-session.

    Different endpoint from /sessions (the legacy V1 list of session inbox dirs)
    to keep backward compat. Future: merge into a single /sessions endpoint.
    """
    from .sessions import collect_sessions
    try:
        return {"host": __import__("socket").gethostname().lower(),
                "sessions": collect_sessions()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/telemetry", dependencies=[Depends(require_token)])
async def telemetry(limit: int = 1000):
    """Return recent telemetry events from ~/.claude/telemetry.jsonl. (token-gated — may contain sensitive tool usage)"""
    import json
    from pathlib import Path
    tfile = Path.home() / ".claude" / "telemetry.jsonl"
    if not tfile.exists():
        return {"events": [], "total": 0}
    lines = tfile.read_text().splitlines()
    events = []
    for line in lines:
        try:
            events.append(json.loads(line))
        except Exception:
            pass
    return {"events": events[-limit:], "total": len(events)}


@app.get("/telemetry/summary", dependencies=[Depends(require_token)])
async def telemetry_summary():
    """Aggregated stats: tool call counts, error rates, slash command counts. (token-gated)"""
    import json
    from collections import defaultdict
    from pathlib import Path
    tfile = Path.home() / ".claude" / "telemetry.jsonl"
    if not tfile.exists():
        return {"tools": {}, "slash_commands": {}, "sessions": 0}
    tools: dict = defaultdict(lambda: {"calls": 0, "errors": 0})
    slash: dict = defaultdict(int)
    sessions = 0
    for line in tfile.read_text().splitlines():
        try:
            e = json.loads(line)
        except Exception:
            continue
        if e.get("event") == "PostToolUse":
            t = e.get("tool", "unknown")
            tools[t]["calls"] += 1
            if not e.get("success", True):
                tools[t]["errors"] += 1
        elif e.get("event") == "UserPromptSubmit" and e.get("slash_cmd"):
            slash[e["slash_cmd"]] += 1
        elif e.get("event") == "Stop":
            sessions += 1
    return {
        "tools": {k: {**v, "error_rate": round(v["errors"]/v["calls"], 3) if v["calls"] else 0}
                  for k, v in sorted(tools.items(), key=lambda x: -x[1]["calls"])},
        "slash_commands": dict(sorted(slash.items(), key=lambda x: -x[1])),
        "sessions": sessions,
    }


@app.get("/transfers/{transfer_id}/content", dependencies=[Depends(require_token)])
async def transfer_content(transfer_id: str):
    """Full content of a transfer (message text + attachment list) — token-gated."""
    import json
    import subprocess
    from pathlib import Path
    msg_show = "/usr/local/bin/msg-show"
    if not Path(msg_show).exists():
        raise HTTPException(status_code=503, detail="tailnet-messaging not installed")
    try:
        r = subprocess.run([msg_show, transfer_id, "--json"],
                           capture_output=True, text=True, timeout=10)
        data = json.loads(r.stdout)
        if "error" in data:
            raise HTTPException(status_code=404, detail=data["error"])
        return data
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="msg-show timeout")
