#!/bin/bash
# Installs tailnet-messaging: symlinks the msg-* commands into /usr/local/bin
# and creates the inbox/archive directories. Idempotent.
set -e

SCRIPT_DIR="$(dirname "$(realpath "$0")")"

for cmd in msg-send msg-receive msg-list msg-archive msg-show; do
    chmod +x "${SCRIPT_DIR}/${cmd}"
    ln -sf "${SCRIPT_DIR}/${cmd}" "/usr/local/bin/${cmd}"
    echo "✓ /usr/local/bin/${cmd}"
done

# Create inbox / archive
mkdir -p "${HOME}/inbox" "${HOME}/taildrops-lus" "${HOME}/.msg-staging"
echo "✓ ${HOME}/inbox/  ${HOME}/taildrops-lus/  créés"

echo
echo "═══════════════════════════════════════════════════════════════════"
echo "tailnet-messaging installé."
echo
echo "  msg-receive              — récupère les taildrops, groupe en transferts"
echo "  msg-list                 — liste les transferts non lus (inbox)"
echo "  msg-send <host> --subject ... --body f.md [--attach ...]"
echo "  msg-archive <id> | --all — marque transfert(s) comme lu(s)"
echo
echo "Convention: après avoir traité un transfert reçu → msg-archive <id>"
echo "═══════════════════════════════════════════════════════════════════"
