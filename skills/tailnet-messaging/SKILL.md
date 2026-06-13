---
name: tailnet-messaging
description: Messagerie inter-agents formalisée pour le tailnet. Envoi et réception de "transferts" (message + pièces jointes groupées). Inbox/archive avec compteur exact de messages non lus. Remplace les taildrops ad-hoc. Use quand un agent envoie/reçoit des messages ou des fichiers à/depuis une autre machine.
---

# tailnet-messaging

Formalise la messagerie inter-claude du tailnet. Avant : `tailscale file cp` ad-hoc + frontmatter manuel, fichiers en vrac dans `/root`, comptage non-lus bancal. Maintenant : transferts groupés, inbox/archive, compteur exact.

## Concept clé — le "transfert"

Un **transfert** = 1 message (`.md` avec frontmatter YAML) + 0..N pièces jointes, traités comme **une unité**. Le frontmatter `attachments:` lie le message à ses fichiers.

```
---
to: main-host
from: ia
subject: Rapport benchmark
priority: normal
requires_reply: no
attachments:
  - benchmark.zip
  - samples.txt
---
# corps du message en markdown
```

## Layout sur chaque machine

```
~/inbox/<transfer-id>/        — transferts reçus NON LUS
     message.md
     <pièces jointes>
~/taildrops-lus/<transfer-id>/  — transferts traités (archive, consultable)
~/.msg-staging/               — zone tampon de réception (interne)
```

**Compteur de messages non lus = nombre de dossiers dans `~/inbox/`.** Exact, zéro heuristique.

## Install

```bash
git clone gitea:skills/tailnet-messaging /root/skills/tailnet-messaging
bash /root/skills/tailnet-messaging/scripts/install.sh
```

Symlink les 4 commandes `msg-*` dans `/usr/local/bin` + crée inbox/archive.

## Commandes

### Recevoir

```bash
msg-receive            # tailscale file get + groupe en transferts dans ~/inbox/
msg-receive --json     # sortie machine-readable
```

Les pièces jointes déclarées dans `attachments:` sont automatiquement regroupées avec leur message. Les fichiers reçus sans message lié → transfert "loose-files".

### Lister

```bash
msg-list               # transferts non lus (~/inbox/)
msg-list --archive     # transferts archivés
msg-list --json        # machine-readable
```

### Envoyer

```bash
msg-send <dest> --subject "Sujet" --body corps.md [--attach f1 f2 ...] \
         [--priority low|normal|high] [--requires-reply] [--in-reply-to <fichier>] \
         [--for-human]

# corps via stdin :
echo "# Mon message" | msg-send <dest> --subject "Sujet" --body -
```

Le script génère/corrige le frontmatter automatiquement (to/from/date/attachments) et envoie message + pièces jointes groupés.

### Flag `--for-human` (transferts à destination de l'humain final)

Quand un agent envoie un fichier à Max **via une machine intermédiaire** (typique : push d'un PDF/screenshot/log vers `shadow-local` ou `desktop-gi54ntg` pour que Max relise sur son PC), le body est une note destinée à Max, **pas** une demande adressée à l'IA réceptrice.

```bash
msg-send shadow-local --for-human --subject "Deck V3 pour relecture" \
  --body /tmp/note-pour-max.md --attach deck-v3.pdf
```

→ ajoute `for_human_only: yes` dans le frontmatter. `msg-list` affiche le tag `[POUR HUMAIN — note pour Max, pas demande IA]`. `msg-show` affiche un encart d'avertissement. **Convention** : l'IA réceptrice stocke les fichiers, archive le transfert, et ne traite **pas** le body comme une demande qui lui est adressée.

### Archiver (marquer comme lu)

```bash
msg-archive <transfer-id>      # archive un transfert
msg-archive --all              # archive tout l'inbox
```

## Convention de flotte

**Après avoir traité un transfert reçu, le claude DOIT l'archiver** :

```bash
msg-archive <transfer-id>
```

→ le compteur de non-lus retombe automatiquement. À ajouter dans le `CLAUDE.md` de chaque machine :

> *Quand tu traites un transfert reçu (`msg-list` pour voir), archive-le après traitement : `msg-archive <id>`.*

## Intégration

- **streamdeck-claude-bridge** : l'agent-local lira `msg-list --json` pour le compteur exact + la liste des transferts (avec expéditeur via le champ `from:` du frontmatter). Le bouton Stream Deck "forcer lecture d'un transfert" déclenchera la lecture ciblée d'un transfert précis.
- **Compteur fiable** : remplace l'ancienne heuristique timestamp de central-aggregator (qui comptait tous les `.md`, d'où les chiffres gonflés type "mailcow 104").

## Limites connues

- L'expéditeur dépend du champ `from:` du frontmatter. Un fichier reçu sans frontmatter → transfert "loose-files", expéditeur "unknown" (`tailscale file cp` ne transmet pas l'expéditeur de façon exploitable).
- `tailscale file cp` vers soi-même est interdit par Tailscale (pas de self-send).
