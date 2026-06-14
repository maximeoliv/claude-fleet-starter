#!/bin/bash
# Installs tailnet-messaging: symlinks the msg-* commands and creates the
# inbox/archive directories. Idempotent.
#
# - As root → symlinks into /usr/local/bin.
# - As user → symlinks into ~/.local/bin (the main install.sh adds this to PATH;
#   if you run the skill standalone, make sure ~/.local/bin is on your PATH).
set -euo pipefail

SCRIPT_DIR="$(dirname "$(realpath "$0")")"

if [[ $EUID -eq 0 ]]; then
    BIN_DIR=/usr/local/bin
else
    BIN_DIR="$HOME/.local/bin"
    mkdir -p "$BIN_DIR"
fi

for cmd in msg-send msg-receive msg-list msg-archive msg-show; do
    chmod +x "${SCRIPT_DIR}/${cmd}"
    ln -sf "${SCRIPT_DIR}/${cmd}" "${BIN_DIR}/${cmd}"
    echo "✓ ${BIN_DIR}/${cmd}"
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

if [[ "$BIN_DIR" == "$HOME/.local/bin" ]] && ! echo ":${PATH:-}:" | grep -q ":$BIN_DIR:"; then
    echo
    echo "⚠ $BIN_DIR n'est pas dans ton PATH. Ajoute :"
    echo '  echo '\''export PATH="$HOME/.local/bin:$PATH"'\'' >> ~/.bashrc && source ~/.bashrc'
fi
