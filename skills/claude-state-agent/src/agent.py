"""claude-state-agent — local HTTP agent exposing this machine's claude state.

Runs on every fleet machine. The central central-aggregator daemon polls this
agent via plain HTTP (GET /state) instead of doing heavy SSH. All state is
generated locally — instant, no SSH latency.
"""
from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import actions
from .local_state import get_local_state
from .models import ActionRequest, InjectRequest, LocalState, SessionInfo

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("claude-state-agent")

app = FastAPI(title="claude-state-agent", version="1.0.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"], allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/state", response_model=LocalState)
async def state():
    """Full local state — claude status, prompt, pressure, transfers."""
    return get_local_state()


@app.post("/action")
async def do_action(req: ActionRequest):
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


@app.post("/claude/start")
async def claude_start():
    """Start claude AND drive it to ready+remote-control (resume = full as-is, verified)."""
    import asyncio
    result = await asyncio.to_thread(actions.ensure_ready)
    return result


@app.post("/claude/ensure-ready")
async def claude_ensure_ready():
    """Explicit: drive claude from any state to ready+remote-control."""
    import asyncio
    result = await asyncio.to_thread(actions.ensure_ready)
    return result


@app.post("/claude/stop")
async def claude_stop():
    return {"ok": actions.claude_stop()}


@app.post("/claude/restart")
async def claude_restart():
    return {"ok": actions.claude_restart()}


@app.post("/transfers/read")
async def transfers_read(transfer_id: str | None = None):
    """Make the local claude read its taildrop transfer(s)."""
    return {"ok": actions.read_transfer(transfer_id), "transfer_id": transfer_id}


@app.post("/transfers/{transfer_id}/archive")
async def transfer_archive(transfer_id: str):
    """Directly archive a transfer (mark-as-read)."""
    return {"ok": actions.archive_transfer(transfer_id), "transfer_id": transfer_id}


@app.get("/sessions", response_model=list[SessionInfo])
async def list_sessions():
    """List all tmux sessions with their claude state."""
    return actions.get_sessions_info()


@app.post("/sessions/{session}/inject")
async def session_inject(session: str, req: InjectRequest):
    """Inject a prompt into a specific named tmux session."""
    ok = actions.inject_into_session(session, req.message)
    return {"ok": ok, "session": session}


@app.post("/sessions/{session}/start")
async def session_start(session: str):
    """Create a tmux session and launch claude inside it."""
    ok = actions.start_named_session(session)
    return {"ok": ok, "session": session}


@app.post("/sessions/{session}/ensure-ready")
async def session_ensure_ready(session: str):
    """Drive a specific tmux session to ready_with_remote_control."""
    import asyncio
    result = await asyncio.to_thread(actions.ensure_ready_session, session)
    return result


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


@app.get("/telemetry")
async def telemetry(limit: int = 1000):
    """Return recent telemetry events from ~/.claude/telemetry.jsonl."""
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


@app.get("/telemetry/summary")
async def telemetry_summary():
    """Aggregated stats: tool call counts, error rates, slash command counts."""
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


@app.get("/transfers/{transfer_id}/content")
async def transfer_content(transfer_id: str):
    """Full content of a transfer (message text + attachment list) — for the dashboard."""
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
