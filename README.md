# claude-fleet-starter

> Kit clé en main pour installer Claude Code et orchestrer plusieurs Claude Code entre plusieurs machines, peu importe ton niveau technique.

**Statut** : Phase 1 (alpha, testé sur Synology DSM). Phase 2 multi-OS arrive après retours utilisateurs.

---

## C'est quoi ?

Si tu utilises [Claude Code](https://claude.com/code) et que tu veux :

- L'installer **proprement sur plusieurs machines** (ton PC, ton NAS, un VPS, etc.)
- **Communiquer entre tes Claude Code** sur différentes machines (envoi de fichiers, messages, etc.)
- Lancer un **2ème, 3ème Claude Code** sur la même machine pour bosser sur plusieurs projets en parallèle
- Avoir un **second cerveau partagé** entre tes Claude Code (patterns, décisions, RETEX...)
- **Recevoir / envoyer des secrets** (mots de passe, clés API) sans qu'ils passent en clair dans tes chats
- Tout ça **sans devoir tout reconfigurer à la main** à chaque nouvelle machine

→ ce kit fait tout ça pour toi en un script.

---

## Installation rapide

### Si tu sais ce que tu fais (mode avancé)

**Linux / macOS / Synology DSM** :

```bash
curl -fsSL https://raw.githubusercontent.com/maximeoliv/claude-fleet-starter/main/install.sh | bash
```

**Windows natif (sans WSL)** — ouvre PowerShell :

```powershell
iwr https://raw.githubusercontent.com/maximeoliv/claude-fleet-starter/main/install.ps1 -UseBasicParsing | iex
```

### Si tu débutes (mode guidé)

- Linux / macOS / Synology : [version pas-à-pas (FR)](docs/install-step-by-step-fr.md) *(à venir)*
- Windows : [guide d'installation Windows (FR)](docs/windows-install-fr.md)

Le script `install.sh` te pose des questions, s'adapte à ton niveau technique, et installe ce qu'il faut. Tu peux à tout moment lui dire "détaille plus", "va plus vite", ou poser une question.

---

## Ce qui est installé

| Composant | À quoi ça sert |
|---|---|
| **Claude Code** | Le CLI officiel d'Anthropic (si tu ne l'as pas déjà) |
| **tailnet-messaging** | Envoie/reçois des messages et fichiers entre tes Claude Code via [Tailscale](https://tailscale.com) (`msg-send`, `msg-receive`) |
| **claude-state-agent** | Petit serveur local qui expose l'état de ton Claude Code (utile pour contrôler depuis ton téléphone, ou monitoring) |
| **claude-launcher** | Lance Claude Code automatiquement au démarrage de ta machine, dans un `tmux` propre |
| **claude-fork** | Lance un 2ème Claude Code à la demande, en mode Remote Control, depuis ta session courante |
| **cerveau** | Second cerveau partagé entre tes Claude Code (notes, patterns, décisions) versionné sur Git |
| **tailscale-secure-form** | Petite page web temporaire pour t'envoyer/recevoir des secrets sans qu'ils passent en clair |
| **skills-autoupdate** | Met à jour les outils ci-dessus automatiquement (chaque nuit) sans rien casser |
| **onboard-tailnet-machine** | Analyse une nouvelle machine et génère son `CLAUDE.md` initial |
| **claude-on-remote** | Démarre / gère des Claude Code sur des machines distantes via Tailscale SSH |

Tu peux activer/désactiver chaque composant au moment de l'installation.

---

## Multi-machine : comment ça marche

L'idée centrale : tu installes ce kit sur **chaque** machine où tu veux avoir un Claude Code. Toutes tes machines se retrouvent dans le **même réseau privé Tailscale** (gratuit, sécurisé). À partir de là :

- Tu peux **envoyer des fichiers** entre tes Claude Code (`msg-send ma-machine-2 --subject "..." --body fichier.md`)
- Tu peux **demander à un Claude Code A de lancer un Claude Code B** sur une autre machine
- Tu peux **chercher dans ton second cerveau** des trucs écrits sur n'importe quelle autre machine

---

## Multi-Claude sur une même machine

Tu peux avoir **plusieurs Claude Code en parallèle** sur la même machine, chacun avec son contexte propre. Exemple :

- Une session "infra" qui gère ton serveur
- Une session "rédaction" qui t'aide à écrire un article
- Une session "code" qui bosse sur un projet

→ La commande `claude-fork` permet de lancer une nouvelle session depuis ta session courante.

---

## Sécurité — à lire avant d'activer Remote Control

Si tu actives le **Remote Control** (= contrôler ton Claude Code depuis ton téléphone via l'app Claude), n'importe qui qui a accès à **ton compte claude.ai** peut piloter à distance les Claude Code de toutes tes machines.

→ Si tu **partages ton compte claude.ai avec quelqu'un** (un membre de ta famille, ton équipe…), il a accès à toutes tes machines.

Détails et bonnes pratiques : [`docs/remote-control-security.md`](docs/remote-control-security.md)

---

## Mises à jour

Le kit s'auto-met à jour chaque nuit via le skill `skills-autoupdate` (si tu l'as activé à l'installation). Les mises à jour sont des `git pull --ff-only` (= si tu as modifié les outils localement, le pull est refusé et tu reçois une notification, rien n'est cassé).

Tu peux désactiver l'auto-update à l'installation. Dans ce cas, tu mets à jour à la main :

```bash
cd ~/.claude-fleet-starter && git pull
```

---

## Langues supportées

- 🇫🇷 Français
- 🇬🇧 English

D'autres langues à venir. Si tu veux contribuer une traduction : voir [`docs/i18n/CONTRIBUTING.md`](docs/i18n/CONTRIBUTING.md).

---

## Désinstallation

```bash
~/.claude-fleet-starter/uninstall.sh
```

Désactive tous les services systemd, supprime les symlinks, et te demande si tu veux supprimer les données (mémoires, second cerveau, configs).

---

## Crédits

Ce kit est extrait de l'infrastructure perso de [@maximeoliv](https://github.com/maximeoliv) et sanitisé pour usage public.

Skills réutilisés et adaptés depuis :
- [tailnet-messaging](https://gitea.tail91a2f7.ts.net/) (privé)
- [claude-state-agent](https://gitea.tail91a2f7.ts.net/) (privé)
- ... etc.

Phase 1 = test avec un utilisateur réel. Phase 2 = sanitisation finale + ajout support Debian/Ubuntu/macOS + annonce publique.

---

## Licence

MIT (à confirmer en Phase 2). Aucune garantie. Use at your own risk.
