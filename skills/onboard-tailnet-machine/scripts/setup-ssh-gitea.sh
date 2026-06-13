#!/bin/bash
# Generates SSH key for this machine, configures ~/.ssh/config to alias Gitea,
# and prints the public key for manual upload to Gitea UI. Idempotent.
set -e

HOSTNAME=$(hostname | tr '[:upper:]' '[:lower:]')
SSH_DIR="${HOME}/.ssh"
KEY_PATH="${SSH_DIR}/${HOSTNAME}_ed25519"
CONFIG_PATH="${SSH_DIR}/config"

mkdir -p "$SSH_DIR"
chmod 700 "$SSH_DIR"

# Generate key if missing
if [[ ! -f "$KEY_PATH" ]]; then
    ssh-keygen -t ed25519 -f "$KEY_PATH" -N '' -C "${HOSTNAME} root onboard-tailnet-machine"
    echo "Generated $KEY_PATH"
else
    echo "Key already exists at $KEY_PATH, reusing"
fi

# Resolve Gitea's tailnet IP via tailscale (system DNS may not pass through magicDNS
# on Proxmox LXCs, so we hardcode the IP — re-run this script if Gitea's IP changes).
GITEA_IP=$(tailscale ip -4 gitea 2>/dev/null | head -1)
if [[ -z "$GITEA_IP" ]]; then
    echo "WARN: tailscale ip -4 gitea returned nothing; falling back to magicDNS name (may fail on LXCs)"
    GITEA_HOST_TARGET="gitea.tail91a2f7.ts.net"
else
    echo "Resolved gitea via tailscale: $GITEA_IP"
    GITEA_HOST_TARGET="$GITEA_IP"
fi

# Add gitea alias if missing
if [[ -f "$CONFIG_PATH" ]] && grep -qE '^\s*Host\s+gitea\s*$' "$CONFIG_PATH"; then
    echo "gitea alias already in $CONFIG_PATH, skipping"
else
    cat >> "$CONFIG_PATH" <<EOF

Host gitea
    HostName ${GITEA_HOST_TARGET}
    Port 2222
    User git
    IdentityFile ${KEY_PATH}
    IdentitiesOnly yes
EOF
    chmod 600 "$CONFIG_PATH"
    echo "Added gitea alias to $CONFIG_PATH (HostName=${GITEA_HOST_TARGET})"
fi

# Add Gitea host key to known_hosts (StrictHostKeyChecking=accept-new on first run)
if ! ssh-keygen -F "[${GITEA_HOST_TARGET}]:2222" -f "${SSH_DIR}/known_hosts" >/dev/null 2>&1; then
    ssh-keyscan -p 2222 -t ed25519,rsa,ecdsa "${GITEA_HOST_TARGET}" 2>/dev/null >> "${SSH_DIR}/known_hosts"
    chmod 600 "${SSH_DIR}/known_hosts"
    echo "Added Gitea host key to known_hosts"
fi

echo
echo "═══════════════════════════════════════════════════════════════════════════"
echo "MANUAL STEP: copy this public key into Gitea UI (User Settings → SSH Keys):"
echo "═══════════════════════════════════════════════════════════════════════════"
cat "${KEY_PATH}.pub"
echo "═══════════════════════════════════════════════════════════════════════════"
echo
echo "Title suggestion: '${HOSTNAME} root'"
echo
echo "Then test:  ssh -T gitea"
echo "Expected:   'Hi there, <you>! You've successfully authenticated...'"
