#!/bin/bash
# Installs the matrix-notify bash function in ~/.bashrc. Idempotent.
set -e

BASHRC="${HOME}/.bashrc"
MARKER_BEGIN='# >>> matrix-notify (onboard-tailnet-machine) >>>'
MARKER_END='# <<< matrix-notify (onboard-tailnet-machine) <<<'

if grep -qF "$MARKER_BEGIN" "$BASHRC" 2>/dev/null; then
    echo "matrix-notify already installed in $BASHRC, skipping"
    exit 0
fi

cat >> "$BASHRC" <<'EOF'

# >>> matrix-notify (onboard-tailnet-machine) >>>
matrix-notify() {
    local level="${1:-info}"
    local msg="${2:-}"
    local room="${3:-alerts-tailnet}"
    if [[ -z "$msg" ]]; then
        echo "Usage: matrix-notify <info|warn|error|success> <message> [room]" >&2
        return 1
    fi
    local src
    src="$(hostname | tr '[:upper:]' '[:lower:]')"
    tailscale ssh root@panels.tail91a2f7.ts.net \
      "bash /root/skills/matrix-notify/notify.sh -l '$level' -r '$room' -s '$src' '$msg'"
}
# <<< matrix-notify (onboard-tailnet-machine) <<<
EOF

echo "matrix-notify function added to $BASHRC"
echo "Run: source ~/.bashrc && matrix-notify info \"hello from \$(hostname)\""
