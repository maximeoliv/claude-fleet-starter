#!/bin/bash
# Install the cerveau skill: clone the repo if not present, symlink CLIs to /usr/local/bin.
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
REPO="$HOME/cerveau-flotte"

# Clone repo if not already cloned
if [[ ! -d "$REPO/.git" ]]; then
    echo "Cloning gitea:runbooks/cerveau-flotte.git into $REPO…"
    git clone gitea:runbooks/cerveau-flotte.git "$REPO"
else
    echo "cerveau-flotte already cloned at $REPO."
fi

# Make scripts executable
chmod +x "$DIR/scripts/"*

# Symlink CLIs
for cmd in cerveau-search cerveau-recent cerveau-write cerveau-list cerveau-pull; do
    ln -sf "$DIR/scripts/$cmd" "/usr/local/bin/$cmd"
    echo "  symlinked /usr/local/bin/$cmd"
done

echo ""
echo "=============================================="
echo "cerveau skill installé."
echo ""
echo "Usage :"
echo "  cerveau-search 'sujet'    # cherche dans le repo"
echo "  cerveau-recent [N]        # changements des N derniers jours (def: 7)"
echo "  cerveau-write <cat> <slug>  # ajoute une nouvelle entrée (catégories: pulse, projects, retex, patterns, decisions, audits)"
echo "  cerveau-list [cat]        # liste les fichiers"
echo "  cerveau-pull              # sync manuel"
echo "=============================================="
