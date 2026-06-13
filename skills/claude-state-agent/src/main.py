"""Entry point — run the agent.

Binds on the machine's tailnet IP when possible. On hosts where Tailscale runs in
userspace-networking mode (typical for unprivileged LXC — e.g. gitea), the tailnet
IP is not a bindable local interface, so we fall back to 0.0.0.0.
"""
from __future__ import annotations

import socket
import subprocess

import uvicorn

PORT = 18920


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


def main() -> None:
    ip = tailnet_ip()
    # Prefer the tailnet IP (tailnet-only exposure). Fall back to 0.0.0.0 if it's
    # not bindable (userspace-networking hosts).
    bind_host = ip if can_bind(ip) else "0.0.0.0"
    uvicorn.run("src.agent:app", host=bind_host, port=PORT,
                log_level="warning", access_log=False)


if __name__ == "__main__":
    main()
