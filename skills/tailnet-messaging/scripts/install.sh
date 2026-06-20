#!/bin/bash
# Installs tailnet-messaging: symlinks the msg-* commands into /usr/local/bin
# and creates the inbox/archive/sent/receipts directories. Idempotent.
set -e

SCRIPT_DIR="$(dirname "$(realpath "$0")")"

# Core commands (existing) + Phase A-F refonte 2026-06-20 (sent/received/thread/awareness)
for cmd in msg-send msg-receive msg-list msg-archive msg-show \
           msg-sent msg-sent-search msg-sent-show \
           msg-received msg-received-search msg-thread \
           messaging-awareness-hook; do
    if [[ -f "${SCRIPT_DIR}/${cmd}" ]]; then
        chmod +x "${SCRIPT_DIR}/${cmd}"
        ln -sf "${SCRIPT_DIR}/${cmd}" "/usr/local/bin/${cmd}"
        echo "✓ /usr/local/bin/${cmd}"
    fi
done

# Create inbox / archive / sent / receipts / status / staging
mkdir -p "${HOME}/inbox" "${HOME}/taildrops-lus" "${HOME}/taildrops-lus/receipts" \
         "${HOME}/taildrops-envoyes" "${HOME}/.msg-staging" "${HOME}/.msg-sent-status"
echo "✓ ~/inbox/  ~/taildrops-lus/{,receipts/}  ~/taildrops-envoyes/  ~/.msg-sent-status/  créés"

echo
echo "═══════════════════════════════════════════════════════════════════"
echo "tailnet-messaging installé."
echo
echo "  Inbox + archive (reçus) :"
echo "    msg-receive              — récupère les taildrops, groupe en transferts"
echo "    msg-list                 — liste l'inbox (non lus)"
echo "    msg-show <id>            — affiche un transfert (inbox OU archivé)"
echo "    msg-archive <id> | --all — archive un transfert (+ auto-receipt au sender)"
echo "    msg-received             — liste les reçus archivés (history)"
echo "    msg-received-search <q>  — full-text dans reçus archivés"
echo
echo "  Envois (Phase B 2026-06-20) :"
echo "    msg-send <host> --subject ... --body f.md [--attach ...] [--kind ...]"
echo "    msg-sent                 — liste les envois récents + status"
echo "    msg-sent-search <q>      — full-text dans envois"
echo "    msg-sent-show <id>       — voir un envoi + son tracker"
echo
echo "  Thread + awareness :"
echo "    msg-thread <id>          — reconstitue le fil complet (sent + reçus + receipts)"
echo "    messaging-awareness-hook — pour ~/.claude/settings.json UserPromptSubmit"
echo
echo "Conventions :"
echo "  - Après traitement d'un reçu → msg-archive <id>"
echo "    (envoie automatiquement un receipt-read au sender, status: read)"
echo "  - Pour un ack léger → msg-send <host> --kind ack --in-reply-to <id>"
echo "═══════════════════════════════════════════════════════════════════"
