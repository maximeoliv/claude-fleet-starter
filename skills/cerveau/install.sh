#!/bin/bash
# Install the cerveau skill.
#
# Clones the shared notes repo if a CERVEAU_REPO env var is provided. By default
# the kit ships without a repo — bring your own (Gitea, GitHub, GitLab, anything
# git understands). Skips the clone step when CERVEAU_REPO is unset, so the CLIs
# still install (they'll just complain there's no repo when invoked).
#
# Symlinks into /usr/local/bin when running as root, otherwise ~/.local/bin.
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
REPO="${CERVEAU_DIR:-$HOME/cerveau-flotte}"

if [[ -n "${CERVEAU_REPO:-}" ]]; then
    if [[ ! -d "$REPO/.git" ]]; then
        echo "Cloning $CERVEAU_REPO into $REPO…"
        git clone "$CERVEAU_REPO" "$REPO"
    else
        echo "cerveau-flotte already cloned at $REPO."
    fi
else
    mkdir -p "$REPO"
    if [[ ! -d "$REPO/.git" ]]; then
        echo "⚠ CERVEAU_REPO non défini → pas de clone. Le dossier $REPO est créé vide."
        echo "  Pour activer la sync : remplis $REPO avec ton repo, ou réinstalle avec"
        echo "  CERVEAU_REPO=ssh://git@ton-host/org/cerveau.git bash install.sh"
    fi
fi

# Make scripts executable
chmod +x "$DIR/scripts/"*

# Resolve bin dir based on privilege.
if [[ $EUID -eq 0 ]]; then
    BIN_DIR=/usr/local/bin
else
    BIN_DIR="$HOME/.local/bin"
    mkdir -p "$BIN_DIR"
fi

for cmd in cerveau-search cerveau-recent cerveau-write cerveau-list cerveau-pull; do
    ln -sf "$DIR/scripts/$cmd" "$BIN_DIR/$cmd"
    echo "  symlinked $BIN_DIR/$cmd"
done

echo ""
echo "=============================================="
echo "cerveau skill installé."
echo ""
echo "Usage :"
echo "  cerveau-search 'sujet'    # cherche dans le repo"
echo "  cerveau-recent [N]        # changements des N derniers jours (def: 7)"
echo "  cerveau-write <cat> <slug>  # ajoute une nouvelle entrée"
echo "                              (catégories: pulse, projects, retex, patterns, decisions, audits)"
echo "  cerveau-list [cat]        # liste les fichiers"
echo "  cerveau-pull              # sync manuel"
echo "=============================================="

if [[ "$BIN_DIR" == "$HOME/.local/bin" ]] && ! echo ":${PATH:-}:" | grep -q ":$BIN_DIR:"; then
    echo
    echo "⚠ $BIN_DIR n'est pas dans ton PATH. Ajoute :"
    echo '  echo '\''export PATH="$HOME/.local/bin:$PATH"'\'' >> ~/.bashrc && source ~/.bashrc'
fi
