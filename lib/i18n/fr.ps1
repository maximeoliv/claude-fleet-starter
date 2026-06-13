# French translations for claude-fleet-starter installer (PowerShell).
# All strings are paragraphs that get rendered via Say / Explain / Confirm.

$T_HEADER = @"

╭─────────────────────────────────────────────────────╮
│  claude-fleet-starter                               │
│                                                     │
│  Kit clé en main pour installer Claude Code et      │
│  orchestrer plusieurs Claude Code entre plusieurs   │
│  machines.                                          │
╰─────────────────────────────────────────────────────╯

"@

$T_OS_DETECTED = "✓ Système d'exploitation détecté : {0}"
$T_CHECKING_DEPS = "Vérification des prérequis (PowerShell 5+, curl, etc.)..."
$T_DEPS_MISSING = "Il manque des outils de base. Lis le message d'erreur juste au-dessus pour savoir quoi installer."

$T_CLAUDE_FOUND = "✓ Claude Code est déjà installé (version : {0})"
$T_INSTALL_CLAUDE = "Tu veux que j'installe Claude Code maintenant ?"
$T_INSTALLING_CLAUDE = "Installation de Claude Code en cours..."
$T_CLAUDE_INSTALLED = "✓ Claude Code installé. Tu pourras le lancer avec la commande : claude"
$T_CLAUDE_SKIPPED = "OK, je n'installe pas Claude Code. Tu pourras le faire plus tard depuis https://claude.com/code"

$T_TAILSCALE_WHAT = @"

Tailscale est un service gratuit qui crée un réseau privé entre tes machines,
comme si elles étaient toutes branchées sur le même routeur Wi-Fi à la maison.
C'est sécurisé (tout est chiffré), facile à installer, et c'est ce qui permettra
à tes Claude Code de plusieurs machines de discuter entre eux.

Tu n'es pas obligé d'avoir Tailscale, mais sans lui, tes Claude Code seront
isolés les uns des autres (= pas de messagerie multi-machine, pas de cerveau
partagé synchronisé, etc.).
"@

$T_TAILSCALE_FOUND = "✓ Tailscale est déjà installé."
$T_INSTALL_TAILSCALE = "Tu veux que j'installe Tailscale ?"
$T_INSTALLING_TAILSCALE = "Téléchargement de Tailscale Windows..."
$T_TAILSCALE_AUTH_NEEDED = @"

Tailscale est installé, mais il faut maintenant le connecter à ton compte.

Copie cette commande, colle-la dans un terminal PowerShell, et appuie sur Entrée :
"@
$T_PRESS_ENTER_WHEN_DONE = "Quand c'est fait, reviens ici et appuie sur Entrée pour continuer..."
$T_TAILSCALE_REMINDER = "⚠ Tu n'as pas installé Tailscale. Tes Claude Code ne pourront pas se parler entre machines."

$T_RC_WHAT = @"

Le Remote Control (= contrôle à distance) te permet de piloter ton Claude Code
depuis ton téléphone (via l'app Claude) ou depuis claude.ai dans ton navigateur.
Pratique pour suivre ce que fait ton Claude Code quand tu n'es pas à ton bureau.
"@

$T_RC_SECURITY_WARNING = @"

⚠ Attention sécurité : si tu partages ton compte claude.ai avec quelqu'un d'autre
(famille, équipe…), cette personne pourra aussi contrôler à distance ton Claude
Code. Tu peux toujours désactiver le Remote Control plus tard si besoin.
"@

$T_ENABLE_RC_AUTOSTART = "Tu veux que j'active le Remote Control au démarrage automatique ?"

$T_SKILLS_QUESTION = "Je vais installer les outils (skills) qui font la magie du kit."

$T_SKILLS_LIST = @"

Les outils inclus :

  • tailnet-messaging  — envoyer/recevoir des messages et fichiers entre tes machines
  • claude-state-agent — petit serveur local qui expose l'état de Claude Code
  • claude-launcher    — lance Claude Code automatiquement au démarrage
  • cerveau            — second cerveau partagé (notes, patterns, décisions)
  • tailscale-secure-form — page web temporaire pour échanger des secrets en sécurité
  • skills-autoupdate  — met à jour les outils ci-dessus chaque nuit
  • onboard-tailnet-machine — analyse une machine et génère son CLAUDE.md
  • claude-on-remote   — démarre/contrôle des Claude Code distants via Tailscale SSH

Tu peux désactiver certains plus tard si tu veux.
"@

$T_INSTALLING_SKILL = "• Installation de {0}..."

$T_INSTALL_MEMORY_STARTER = "Tu veux que j'installe 3-4 mémoires de démarrage (règles génériques de sécurité et bonnes pratiques) ?"
$T_MEMORY_INSTALLED = "✓ Mémoires de démarrage installées dans %USERPROFILE%\.claude\projects\...\memory\"

$T_BOOTSTRAP_QUESTION = "Tu as déjà utilisé Claude Cowork, Claude Code, ChatGPT, etc. ?"

$T_BOOTSTRAP_WHAT = @"

Si oui, je peux analyser ton historique de discussions pour générer
automatiquement ton fichier CLAUDE.md (= la fiche d'identité de ta machine,
ce que tu fais, comment tu aimes travailler avec une IA, etc.). C'est un
gros gain de temps : Claude Code partira avec ton contexte déjà chargé.
"@

$T_BOOTSTRAP_HAS_HISTORY = "Tu as un dossier qui contient cet historique ?"
$T_BOOTSTRAP_PATH_PROMPT = "OK. Donne-moi le chemin du dossier (ex: C:\Users\toi\Documents\claude-history) :"
$T_BOOTSTRAP_PATH_INVALID = "⚠ Le chemin {0} n'existe pas, je passe."
$T_BOOTSTRAP_RUNNING = "Le bootstrap se lance à ton premier lancement de Claude Code."
$T_BOOTSTRAP_INSTRUCTIONS = @"

Quand tu lanceras Claude Code la première fois, tu lui diras :

  Analyse mon historique dans {0} et génère mon CLAUDE.md selon les
  instructions de bootstrap/analyze-history.md.

Il fera le reste.
"@

$T_DONE_BANNER = @"

╭─────────────────────────────────────────────────────╮
│  ✓ Installation terminée                            │
╰─────────────────────────────────────────────────────╯

"@

$T_NEXT_STEPS = "Prochaines étapes :"
$T_DOCS = "📖 Documentation et aide :"
$T_SETTING_UP_RC_AUTOSTART = "Configuration du Remote Control au démarrage..."
