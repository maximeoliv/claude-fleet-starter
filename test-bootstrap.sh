#!/usr/bin/env bash
# Bootstrap pour tester claude-fleet-starter sur une machine fraîche
# (= machine où Claude Code n'est pas encore installé).
#
# Pour le testeur : une seule commande à lancer
#
#     curl -fsSL https://raw.githubusercontent.com/maximeoliv/claude-fleet-starter/main/test-bootstrap.sh | bash
#
# Le script installe Claude Code, télécharge le prompt de test, et te dit
# les 2 commandes que tu dois taper après pour lancer le test.

set -e

C_RESET='\033[0m'
C_BOLD='\033[1m'
C_GREEN='\033[32m'
C_BLUE='\033[34m'
C_YELLOW='\033[33m'

REPO="https://raw.githubusercontent.com/maximeoliv/claude-fleet-starter/main"

echo
echo -e "${C_BLUE}╭─────────────────────────────────────────────────────────────╮${C_RESET}"
echo -e "${C_BLUE}│  claude-fleet-starter — bootstrap test                      │${C_RESET}"
echo -e "${C_BLUE}╰─────────────────────────────────────────────────────────────╯${C_RESET}"
echo

# ── 1. Vérifier les prérequis basiques ────────────────────────────────────────
missing=()
for cmd in curl bash python3; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
        missing+=("$cmd")
    fi
done
if (( ${#missing[@]} > 0 )); then
    echo -e "${C_YELLOW}⚠ Il te manque ces outils de base : ${missing[*]}${C_RESET}"
    echo "Installe-les avant de continuer :"
    echo "  - Debian/Ubuntu/Pop : sudo apt-get install ${missing[*]}"
    echo "  - macOS             : brew install ${missing[*]}"
    echo "  - Synology DSM      : installe via Package Center ou Container Manager"
    exit 1
fi

# ── 2. Installer Claude Code si pas présent ───────────────────────────────────
if command -v claude >/dev/null 2>&1; then
    echo -e "${C_GREEN}✓ Claude Code est déjà installé.${C_RESET}"
    claude --version 2>&1 | head -1
else
    echo "→ Installation de Claude Code..."
    curl -fsSL https://claude.ai/install.sh | bash
    # Make sure PATH is updated
    export PATH="$HOME/.local/bin:$PATH"
    if ! grep -q '$HOME/.local/bin' "$HOME/.bashrc" 2>/dev/null; then
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
    fi
    if command -v claude >/dev/null 2>&1; then
        echo -e "${C_GREEN}✓ Claude Code installé.${C_RESET}"
        claude --version 2>&1 | head -1
    else
        echo -e "${C_YELLOW}⚠ L'installation de Claude Code semble avoir échoué.${C_RESET}"
        echo "Relance ce script ou installe manuellement depuis https://claude.com/code"
        exit 1
    fi
fi

# ── 3. Télécharger le prompt de test ──────────────────────────────────────────
PROMPT_FILE="/tmp/cfs-test-prompt.txt"
echo "→ Téléchargement du prompt de test..."
curl -fsSL "$REPO/docs/test-feedback-prompt-fr.md" -o /tmp/cfs-test-doc.md

# Extract just the code block (between "## 📋 Prompt à coller" and the closing ```)
python3 << PYEOF
import re
src = open('/tmp/cfs-test-doc.md').read()
m = re.search(r'## 📋 Prompt à coller\s*\n\s*\`\`\`\s*\n(.*?)\n\`\`\`', src, re.DOTALL)
if m:
    open('$PROMPT_FILE', 'w').write(m.group(1).strip())
    print('✓ Prompt sauvegardé dans $PROMPT_FILE (' + str(len(m.group(1))) + ' caractères)')
else:
    print('⚠ Impossible d''extraire le prompt — le fichier source a peut-être changé')
    import sys; sys.exit(1)
PYEOF

# ── 4. Instructions finales ───────────────────────────────────────────────────
echo
echo -e "${C_GREEN}╭─────────────────────────────────────────────────────────────╮${C_RESET}"
echo -e "${C_GREEN}│  ✓ Tout est prêt                                            │${C_RESET}"
echo -e "${C_GREEN}╰─────────────────────────────────────────────────────────────╯${C_RESET}"
echo
echo -e "${C_BOLD}Maintenant 2 commandes à taper toi-même dans ton terminal :${C_RESET}"
echo
echo -e "  ${C_BLUE}1.${C_RESET} Connecte-toi à ton compte Claude (compte personnel ou pro) :"
echo
echo -e "       ${C_BOLD}claude login${C_RESET}"
echo
echo "     (un lien va s'ouvrir dans ton navigateur, suis-le, valide, reviens ici)"
echo
echo -e "  ${C_BLUE}2.${C_RESET} Une fois connecté, lance le test :"
echo
echo -e "       ${C_BOLD}claude < $PROMPT_FILE${C_RESET}"
echo
echo "     Claude va prendre le prompt en entrée et te guider pour le test."
echo
echo -e "${C_YELLOW}💡 Conseil :${C_RESET} si tu peux, lance ça dans un conteneur Docker propre ou"
echo "   une VM, pas sur une machine importante. Le kit installe pas mal de"
echo "   choses et c'est encore en alpha."
echo
echo "   Pour démarrer un conteneur Docker propre :"
echo -e "       ${C_BOLD}docker run -it --rm debian:12 bash${C_RESET}"
echo
echo "   Puis relance ce script à l'intérieur."
echo
echo -e "${C_BOLD}Sois honnête et direct dans tes retours.${C_RESET} Maxime préfère un retour qui"
echo "pique à un retour poli qui ne sert à rien. Le but est de trouver les"
echo "vrais problèmes avant la version publique."
echo
