"""Local actions — tmux send-keys on this machine's "claude" session (no SSH)."""
from __future__ import annotations

import json
import logging
import subprocess
import time
from pathlib import Path

from .parser import detect_state_label
from .resume_nav import plan_navigation, verify_on_target

logger = logging.getLogger("claude-state-agent.actions")

TMUX_SESSION = "claude"
MSG_ARCHIVE_BIN = "/usr/local/bin/msg-archive"
MSG_LIST_BIN = "/usr/local/bin/msg-list"
MSG_RECEIVE_BIN = "/usr/local/bin/msg-receive"
PANE_LINES = 50


def _send_keys(*keys: str) -> bool:
    """Send keystrokes to the local tmux 'claude' session."""
    args = ["tmux", "send-keys", "-t", TMUX_SESSION]
    for k in keys:
        args.append(k)
    try:
        r = subprocess.run(args, capture_output=True, timeout=5)
        return r.returncode == 0
    except Exception:
        return False


def _tmux(*args: str, timeout: float = 8) -> bool:
    try:
        r = subprocess.run(["tmux", *args], capture_output=True, timeout=timeout)
        return r.returncode == 0
    except Exception:
        return False


def _has_session() -> bool:
    return _tmux("has-session", "-t", TMUX_SESSION, timeout=5)


# ── Permission prompt actions ────────────────────────────────────────────────

def accept_once() -> bool:
    """Confirm the default option of a permission prompt. Claude always opens
    the menu with the cursor on option 1 ('Yes'), so a bare Enter confirms it.
    Sending the digit '1' first proved unreliable (observed on ia 16/05: the
    digit keypress didn't register against an already-selected option, the
    prompt stayed stuck — bare Enter cleared it instantly)."""
    return _send_keys("Enter")


def accept_all() -> bool:
    """Select option 2 ('Yes, and don't ask again') — one Down from the default
    cursor, then Enter. Sent as two separate keystrokes so the TUI registers
    the cursor move before the confirm."""
    ok1 = _send_keys("Down")
    time.sleep(0.3)
    ok2 = _send_keys("Enter")
    return ok1 and ok2


def reject() -> bool:
    return _send_keys("Escape")


def send_esc() -> bool:
    return _send_keys("Escape")


def send_compact() -> bool:
    return _send_keys("/compact", "Enter")


def send_clear() -> bool:
    return _send_keys("/clear", "Enter")


# ── Claude lifecycle ─────────────────────────────────────────────────────────

def claude_start() -> bool:
    """Start claude via claude-launcher.service; no-op if already running."""
    if _has_session():
        return True
    try:
        r = subprocess.run(["systemctl", "start", "claude-launcher.service"],
                           capture_output=True, timeout=15)
        return r.returncode == 0
    except Exception:
        return False


def claude_stop() -> bool:
    """Ctrl-C twice then kill the tmux session."""
    _send_keys("C-c")
    time.sleep(0.6)
    _send_keys("C-c")
    time.sleep(1.5)
    return _tmux("kill-session", "-t", TMUX_SESSION)


def claude_restart() -> bool:
    claude_stop()
    time.sleep(2)
    return claude_start()


def _capture_pane() -> str:
    try:
        r_vis = subprocess.run(
            ["tmux", "capture-pane", "-t", TMUX_SESSION, "-p"],
            capture_output=True, text=True, timeout=6,
        )
        r_scroll = subprocess.run(
            ["tmux", "capture-pane", "-t", TMUX_SESSION, "-p", "-S", f"-{PANE_LINES}"],
            capture_output=True, text=True, timeout=6,
        )
        return (r_vis.stdout or "") + "\n" + (r_scroll.stdout or "")
    except Exception:
        return ""


def ensure_ready(max_wait: int = 100) -> dict:
    """Drive the local claude code up to 'ready_with_remote_control'. Sync — run via
    asyncio.to_thread from the endpoint so it doesn't block the event loop.

    Safety: on the resume-mode screen, navigates to "full session as-is" WITH
    verification (re-captures, confirms the cursor) before pressing Enter. Never
    blind-confirms — aborts rather than risk a wrong "from summary" choice.
    """
    log: list[str] = []

    def step(m: str):
        log.append(m)
        logger.info("[ensure_ready] %s", m)

    if not _has_session():
        step("no tmux session — starting claude")
        if not claude_start():
            return {"ok": False, "final_state": "start_failed", "log": log}
        time.sleep(8)

    deadline = time.time() + max_wait
    last_label, stuck = None, 0

    while time.time() < deadline:
        pane = _capture_pane()
        label = detect_state_label(pane)

        if label == last_label:
            stuck += 1
        else:
            stuck = 0
            last_label = label
            step(f"state: {label}")

        if stuck > (40 if label == "busy" else 6):
            return {"ok": False, "final_state": f"stuck:{label}", "log": log}

        if label == "trust_folder":
            _send_keys("Enter"); time.sleep(2); continue

        if label == "resume_picker":
            _send_keys("Enter"); time.sleep(3); continue

        if label == "resume_mode_choice":
            # VERIFIED navigation to "Resume full session as-is" — never blind Enter.
            plan = plan_navigation(pane, "full", "session", "as-is")
            if not plan["ok"]:
                step(f"ABORT resume nav: {plan['reason']}")
                return {"ok": False, "final_state": "resume_nav_failed",
                        "reason": plan["reason"], "log": log}
            for _ in range(plan["presses"]):
                _send_keys(plan["key"]); time.sleep(0.35)
            pane2 = _capture_pane()
            if not verify_on_target(pane2, "full", "session", "as-is"):
                step("ABORT: cursor not verified on 'full session as-is'")
                return {"ok": False, "final_state": "resume_verify_failed", "log": log}
            step("verified cursor on 'full session as-is' -> Enter")
            _send_keys("Enter"); time.sleep(3); continue

        if label == "busy":
            time.sleep(3); continue

        if label in ("ready_no_remote_control", "ready_unknown_remote_control"):
            _send_keys("/remote-control", "Enter"); time.sleep(4)
            _send_keys("Enter"); time.sleep(2)
            continue

        if label == "ready_with_remote_control":
            step("ready with remote-control OK")
            return {"ok": True, "final_state": label, "log": log}

        if label == "oauth_pending":
            return {"ok": False, "final_state": "oauth_pending",
                    "reason": "OAuth login required - manual", "log": log}

        time.sleep(2)

    return {"ok": False, "final_state": f"timeout:{last_label}", "log": log}


# ── Taildrop transfer reading ────────────────────────────────────────────────

def _inbox_summary() -> tuple[int, list[str]]:
    """Pull new taildrops (msg-receive) then return (count, unique sender names)
    of the inbox via msg-list --json. Empty/(0,[]) if the skill isn't installed."""
    if Path(MSG_RECEIVE_BIN).exists():
        try:
            subprocess.run([MSG_RECEIVE_BIN], capture_output=True, timeout=25)
        except Exception:
            pass
    if not Path(MSG_LIST_BIN).exists():
        return 0, []
    try:
        r = subprocess.run([MSG_LIST_BIN, "--json"], capture_output=True,
                           text=True, timeout=10)
        data = json.loads(r.stdout)
        transfers = data.get("transfers", [])
        senders = list(dict.fromkeys((t.get("sender") or "?") for t in transfers))
        return data.get("count", len(transfers)), senders
    except Exception:
        return 0, []


def read_transfer(transfer_id: str | None = None) -> bool:
    """Paste a message in the claude chat asking it to read its taildrop transfer(s).

    If transfer_id given, ask for that specific transfer; otherwise all — in which
    case the message is enriched with the pending count + sender names.
    After claude processes, it should run `msg-archive <id>` itself (fleet convention).
    """
    if transfer_id:
        msg = (f"Traite le transfert {transfer_id} de ton inbox tailnet-messaging "
               f"(`msg-show {transfer_id}` pour le lire). "
               f"Archive-le après traitement: `msg-archive {transfer_id}`")
    else:
        count, senders = _inbox_summary()
        if count == 0:
            # Nothing to read — don't inject noise into the claude session.
            return True
        who = ", ".join(senders[:6]) + ("…" if len(senders) > 6 else "")
        msg = (f"Tu as {count} transfert(s) en attente dans ton inbox tailnet-messaging "
               f"(de: {who}). Traite-les: `msg-list` pour les voir, `msg-show <id>` "
               f"pour lire chacun, puis `msg-archive <id>` une fois traité.")

    ts = int(time.time() * 1000)
    tmp = Path(f"/tmp/.csa-msg-{ts}.txt")
    try:
        tmp.write_text(msg)
        ok1 = _tmux("load-buffer", str(tmp))
        ok2 = _tmux("paste-buffer", "-t", TMUX_SESSION)
        time.sleep(0.5)
        ok3 = _send_keys("Enter")
        return ok1 and ok2 and ok3
    finally:
        tmp.unlink(missing_ok=True)


def archive_transfer(transfer_id: str) -> bool:
    """Directly archive a transfer (mark-as-read without making claude read it)."""
    if not Path(MSG_ARCHIVE_BIN).exists():
        return False
    try:
        r = subprocess.run([MSG_ARCHIVE_BIN, transfer_id], capture_output=True, timeout=10)
        return r.returncode == 0
    except Exception:
        return False


# ── Multi-session support ────────────────────────────────────────────────────

def list_tmux_sessions() -> list[str]:
    """Return names of all active tmux sessions."""
    try:
        r = subprocess.run(
            ["tmux", "list-sessions", "-F", "#{session_name}"],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode != 0:
            return []
        return [s.strip() for s in r.stdout.splitlines() if s.strip()]
    except Exception:
        return []


def _capture_pane_session(session: str) -> str:
    try:
        r_vis = subprocess.run(
            ["tmux", "capture-pane", "-t", session, "-p"],
            capture_output=True, text=True, timeout=6,
        )
        r_scroll = subprocess.run(
            ["tmux", "capture-pane", "-t", session, "-p", "-S", f"-{PANE_LINES}"],
            capture_output=True, text=True, timeout=6,
        )
        return (r_vis.stdout or "") + "\n" + (r_scroll.stdout or "")
    except Exception:
        return ""


def get_sessions_info() -> list[dict]:
    """Return state info for every active tmux session."""
    from .parser import remote_control_active
    sessions = list_tmux_sessions()
    result = []
    for name in sessions:
        pane = _capture_pane_session(name)
        label = detect_state_label(pane)
        claude_running = label in (
            "ready_with_remote_control", "ready_no_remote_control",
            "ready_unknown_remote_control", "permission_prompt",
            "resume_picker", "resume_mode_choice", "trust_folder",
            "oauth_pending", "busy", "starting",
        )
        result.append({
            "name": name,
            "claude_running": claude_running,
            "remote_control": remote_control_active(pane),
            "state_label": label,
        })
    return result


def inject_into_session(session: str, message: str) -> bool:
    """Paste a message into an arbitrary named tmux session."""
    ts = int(time.time() * 1000)
    tmp = Path(f"/tmp/.csa-inject-{ts}.txt")
    try:
        tmp.write_text(message)
        ok1 = _tmux("load-buffer", str(tmp))
        ok2 = _tmux("paste-buffer", "-t", session)
        time.sleep(0.3)
        ok3 = subprocess.run(
            ["tmux", "send-keys", "-t", session, "Enter"],
            capture_output=True, timeout=5,
        ).returncode == 0
        return ok1 and ok2 and ok3
    except Exception:
        return False
    finally:
        tmp.unlink(missing_ok=True)


def start_named_session(session: str) -> bool:
    """Create a new tmux session and launch claude inside (with --remote-control)."""
    import json as _json
    import socket

    # Resolve hostname (same logic as local_state._hostname)
    try:
        out = subprocess.check_output(
            ["tailscale", "status", "--self", "--json"], timeout=5, text=True,
        )
        hostname = _json.loads(out)["Self"].get("HostName", socket.gethostname()).lower()
    except Exception:
        hostname = socket.gethostname().lower()

    # Find claude binary
    claude_bin = "claude"
    for cand in ["/root/.local/bin/claude", "/usr/local/bin/claude", "/usr/bin/claude"]:
        if Path(cand).is_file():
            claude_bin = cand
            break

    try:
        # Create detached session if it doesn't exist
        r = subprocess.run(["tmux", "has-session", "-t", session],
                           capture_output=True, timeout=5)
        if r.returncode != 0:
            subprocess.run(
                ["tmux", "new-session", "-d", "-s", session, "-x", "200", "-y", "50", "-c", "/root"],
                capture_output=True, timeout=10, check=True,
            )

        # Force UTF-8 locale then launch claude
        subprocess.run(["tmux", "send-keys", "-t", session,
                        "export LANG=C.UTF-8 LC_ALL=C.UTF-8", "Enter"],
                       capture_output=True, timeout=5)
        time.sleep(0.5)
        cmd = f'{claude_bin} -c --remote-control "{hostname}" || {claude_bin} --remote-control "{hostname}"'
        subprocess.run(["tmux", "send-keys", "-t", session, cmd, "Enter"],
                       capture_output=True, timeout=5)
        return True
    except Exception as e:
        logger.error("start_named_session(%s): %s", session, e)
        return False


def ensure_ready_session(session: str, max_wait: int = 100) -> dict:
    """Drive an arbitrary named tmux session to ready_with_remote_control."""
    log: list[str] = []

    def step(m: str):
        log.append(m)
        logger.info("[ensure_ready_session:%s] %s", session, m)

    try:
        r = subprocess.run(["tmux", "has-session", "-t", session],
                           capture_output=True, timeout=5)
        if r.returncode != 0:
            step("session not found — starting")
            if not start_named_session(session):
                return {"ok": False, "final_state": "start_failed", "log": log}
            time.sleep(8)
    except Exception:
        return {"ok": False, "final_state": "tmux_error", "log": log}

    from .parser import remote_control_active
    deadline = time.time() + max_wait
    last_label, stuck = None, 0

    while time.time() < deadline:
        pane = _capture_pane_session(session)
        label = detect_state_label(pane)

        if label == last_label:
            stuck += 1
        else:
            stuck = 0
            last_label = label
            step(f"state: {label}")

        if stuck > (40 if label == "busy" else 6):
            return {"ok": False, "final_state": f"stuck:{label}", "log": log}

        def _send(key: str):
            subprocess.run(["tmux", "send-keys", "-t", session, key, ""],
                           capture_output=True, timeout=5)

        if label == "trust_folder":
            _send("Enter"); time.sleep(2); continue

        if label == "resume_picker":
            _send("Enter"); time.sleep(3); continue

        if label == "resume_mode_choice":
            plan = plan_navigation(pane, "full", "session", "as-is")
            if not plan["ok"]:
                return {"ok": False, "final_state": "resume_nav_failed",
                        "reason": plan["reason"], "log": log}
            for _ in range(plan["presses"]):
                _send(plan["key"]); time.sleep(0.35)
            pane2 = _capture_pane_session(session)
            if not verify_on_target(pane2, "full", "session", "as-is"):
                return {"ok": False, "final_state": "resume_verify_failed", "log": log}
            step("verified cursor on 'full session as-is' -> Enter")
            _send("Enter"); time.sleep(3); continue

        if label == "busy":
            time.sleep(3); continue

        if label in ("ready_no_remote_control", "ready_unknown_remote_control"):
            _send("/remote-control"); time.sleep(0.2); _send("Enter"); time.sleep(4)
            _send("Enter"); time.sleep(2); continue

        if label == "ready_with_remote_control":
            step("ready with remote-control OK")
            return {"ok": True, "final_state": label, "log": log}

        if label == "oauth_pending":
            return {"ok": False, "final_state": "oauth_pending",
                    "reason": "OAuth login required - manual", "log": log}

        time.sleep(2)

    return {"ok": False, "final_state": f"timeout:{last_label}", "log": log}
