# cerveau — accès au second cerveau partagé de la flotte

CLI minimal pour lire et écrire dans `gitea:runbooks/cerveau-flotte.git`.

## Pourquoi

Aujourd'hui chaque machine de la flotte avance dans son silo. Les patterns, décisions, RETEX et avancées projet restent dans la mémoire perso de l'agent → personne d'autre ne sait. Ce skill donne accès au **second cerveau partagé** (source de vérité commune).

Voir le `README.md` du repo `cerveau-flotte` pour la convention de structure.

## Installation

```bash
cd /root/skills
git clone gitea:skills/cerveau.git
cd cerveau
bash install.sh
```

L'install clone aussi `gitea:runbooks/cerveau-flotte.git` dans `~/cerveau-flotte/` et symlink les 5 CLIs dans `/usr/local/bin/`.

## Commandes

```bash
cerveau-search "sujet"              # grep + ranking, top 10 fichiers
cerveau-search "sujet" --category patterns  # restreint à une catégorie
cerveau-recent                      # changements des 7 derniers jours
cerveau-recent 30                   # 30 derniers jours
cerveau-write <category> <slug>     # ouvre l'éditeur, commit + push
cerveau-write retex 2026-05-19-gosom --file /tmp/retex.md  # body depuis fichier
echo "..." | cerveau-write patterns mon-pattern --stdin
cerveau-list                        # résumé toutes catégories
cerveau-list projects               # détail d'une catégorie
cerveau-pull                        # sync manuel (sinon skills-autoupdate quotidien)
```

## Catégories

- `pulse/<année>-W<semaine>/<host>.md` — pulse hebdo auto (à venir)
- `projects/<projet>/...` — projets flotte en cours
- `retex/<date>-<sujet>.md` — retours post-incident
- `patterns/<nom>.md` — patterns validés cross-machines
- `decisions/<date>-<sujet>.md` — décisions actées
- `audits/<période>/<host>.md` — audits récurrents

## Workflow type

**Démarrer un nouveau projet** :
```bash
cerveau-search "rename"   # voir s'il y a déjà du contexte
cerveau-recent 14         # quoi de neuf sur la flotte les 2 dernières semaines
cerveau-write projects "rename-foo/2026-06-10-byh-dell1-notes"
```

**Documenter une décision flotte** :
```bash
cerveau-write decisions "2026-06-09-rename-sandbox-agents"
```

**Post-incident** :
```bash
cerveau-write retex "2026-06-09-guacamole-lxc-freeze"
```

## Sync auto

`skills-autoupdate` (déployé sur la flotte) ne pull pas automatiquement `cerveau-flotte` car ce n'est pas un skill — c'est de la doc. Pour automatiser :

- Soit ajouter `~/cerveau-flotte` à la liste auto-pull (modif minimale de `skills-autoupdate.sh`)
- Soit cron systemd dédié dans ce skill (à coder si pertinent)

Pour l'instant, **pull manuel ou au démarrage de session** : `cerveau-pull`.
