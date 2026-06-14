"""Entry point — run the agent.

Bind defaults to **127.0.0.1** (loopback only). To expose the agent on the
tailnet so a central dashboard can poll it, set `CLAUDE_FLEET_BIND=tailnet` in
the environment (the systemd unit reads `/etc/default/claude-state-agent` for
this). `CLAUDE_FLEET_BIND=0.0.0.0` is also possible but **strongly discouraged**
— without a token in front of the mutation endpoints, this would expose remote
control to the entire LAN.
"""
from __future__ import annotations

import logging
import os
import socket
import subprocess

import uvicorn

PORT = 18920
logger = logging.getLogger("claude-state-agent.main")


def tailnet_ip() -> str:
    try:
        out = subprocess.check_output(["tailscale", "ip", "-4"], timeout=5, text=True)
        return out.strip().splitlines()[0]
    except Exception:
        return ""


def can_bind(host: str) -> bool:
    """Check whether `host` is a bindable local address."""
    if not host:
        return False
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((host, 0))
        s.close()
        return True
    except OSError:
        return False


def resolve_bind() -> str:
    """Pick a bind address. Default = 127.0.0.1 (safe). Opt-in tailnet/0.0.0.0 via env."""
    mode = os.environ.get("CLAUDE_FLEET_BIND", "loopback").strip().lower()
    if mode in ("loopback", "localhost", "127.0.0.1", ""):
        return "127.0.0.1"
    if mode in ("tailnet", "ts"):
        ip = tailnet_ip()
        if can_bind(ip):
            return ip
        logger.warning(
            "CLAUDE_FLEET_BIND=tailnet requested but tailnet IP %r isn't bindable "
            "(userspace-networking?) — falling back to 127.0.0.1. Front the agent "
            "with `tailscale serve` to expose it.",
            ip,
        )
        return "127.0.0.1"
    if mode in ("0.0.0.0", "any", "all"):
        logger.warning(
            "CLAUDE_FLEET_BIND=0.0.0.0 — agent exposed on every interface. "
            "Token auth on mutation endpoints is your only protection."
        )
        return "0.0.0.0"
    return "127.0.0.1"


def main() -> None:
    bind_host = resolve_bind()
    if not os.environ.get("CLAUDE_FLEET_STATE_TOKEN", "").strip():
        logger.warning(
            "CLAUDE_FLEET_STATE_TOKEN is empty — every mutation endpoint will "
            "respond 503. Set it in /etc/default/claude-state-agent (or env) and restart."
        )
    uvicorn.run("src.agent:app", host=bind_host, port=PORT,
                log_level="warning", access_log=False)


if __name__ == "__main__":
    main()
