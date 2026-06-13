#!/bin/bash
# Installs claude-state-agent on this machine. Idempotent.
# Uses uv (auto-installed if missing) — uv bundles its own Python, robust across
# the heterogeneous fleet (no python3.X-venv apt hassle).
set -e

SKILL_DIR="$(dirname "$(realpath "$0")")"
cd "$SKILL_DIR"

# 0. Ensure uv is available
UV_BIN=""
for cand in /root/.local/bin/uv /usr/local/bin/uv "$(command -v uv 2>/dev/null)"; do
    if [[ -n "$cand" && -x "$cand" ]]; then UV_BIN="$cand"; break; fi
done
if [[ -z "$UV_BIN" ]]; then
    echo "Installing uv..."
    curl -fsSL https://astral.sh/uv/install.sh | sh 2>&1 | tail -2
    UV_BIN="/root/.local/bin/uv"
fi
echo "✓ uv: $UV_BIN"

# 1. Create venv + install deps via uv
"$UV_BIN" venv --python 3.12 .venv 2>&1 | tail -1
"$UV_BIN" pip install --python .venv/bin/python \
    fastapi "uvicorn[standard]" pydantic httpx 2>&1 | tail -2
echo "✓ dépendances installées"

# 2. systemd service
cp systemd/claude-state-agent.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now claude-state-agent.service

sleep 3
if systemctl is-active --quiet claude-state-agent.service; then
    IP=$(tailscale ip -4 2>/dev/null | head -1)
    echo "✓ claude-state-agent actif sur http://${IP}:18920"
else
    echo "✗ claude-state-agent n'a pas démarré — journalctl -u claude-state-agent -n 20"
    exit 1
fi
