"""Token authentication for mutation/sensitive endpoints.

The state-agent exposes both read-only (`/state`, `/health`, `/sessions`) and
*mutation* endpoints (`/action`, `/sessions/{s}/inject`, `/claude/start`, ...) that
remote-control the local Claude Code. Mutation endpoints MUST require a shared
token — without it, anyone able to reach the port (LAN, tailnet, or worse) can
pilot Claude.

The token is loaded from the `CLAUDE_FLEET_STATE_TOKEN` env var (set by the
systemd unit, sourced from `~/.claude-fleet-starter/state-agent.token`). If the
env var is unset or empty, all mutation endpoints fail closed with 503.
"""
from __future__ import annotations

import hmac
import os

from fastapi import Header, HTTPException


def _expected_token() -> str:
    return os.environ.get("CLAUDE_FLEET_STATE_TOKEN", "").strip()


def require_token(x_fleet_token: str | None = Header(default=None)) -> None:
    """FastAPI dependency: enforce `X-Fleet-Token` header matches the configured token."""
    expected = _expected_token()
    if not expected:
        raise HTTPException(
            status_code=503,
            detail=(
                "state-agent token not configured — mutation endpoints disabled. "
                "Set CLAUDE_FLEET_STATE_TOKEN in the systemd unit (or env) and restart."
            ),
        )
    presented = (x_fleet_token or "").strip()
    if not presented or not hmac.compare_digest(presented, expected):
        raise HTTPException(status_code=401, detail="invalid or missing X-Fleet-Token")


def accept_all_enabled() -> bool:
    """`accept_all` (= 'Yes, don't ask again' piloted remotely) is opt-in only."""
    return os.environ.get("CLAUDE_FLEET_ALLOW_ACCEPT_ALL", "").strip() in ("1", "true", "yes")
