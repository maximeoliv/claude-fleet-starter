# skills-autoupdate

Tâche systemd qui fait un `git pull --ff-only` quotidien sur chaque skill cloné dans `/root/skills/`. Notifie `byh-dell1` via `msg-send` quand quelque chose change.

## Rôle

Sur la flotte tailnet de Max, chaque machine clone ses skills depuis `gitea:skills/*.git`. Quand un skill est mis à jour côté Gitea (par exemple `tailnet-messaging` qui passe en V3 avec le flag `--for-human`), chaque machine devait jusqu'ici pull manuellement. Lent + irrégulier + risque que des fixes critiques (race conditions, etc.) ne soient pas propagés.

Ce skill résout ça : un timer systemd quotidien fait le pull, log tout, et envoie une notif `msg-send byh-dell1` quand quelque chose a été mis à jour.

## Installation

```bash
cd /root/skills
git clone gitea:skills/skills-autoupdate.git
cd skills-autoupdate
bash install.sh
```

Active le timer immédiatement. Premier run au prochain 4h du mat.

## Run manuel

```bash
systemctl start skills-autoupdate.service
tail -f /var/log/skills-autoupdate.log
```

## Architecture

- `scripts/autoupdate.sh` — script principal (bash)
- `systemd/skills-autoupdate.service` — oneshot service qui lance le script
- `systemd/skills-autoupdate.timer` — timer quotidien 04:00 (avec jitter aléatoire 0-30min)
- `install.sh` — symlink les units dans `/etc/systemd/system/`, daemon-reload, enable --now

## Comportement

Pour chaque sous-dossier de `/root/skills/` qui a un `.git/` :

1. `git fetch origin` (échec → noté en `failures`, on continue)
2. `git pull --ff-only origin main` (échec si modifs locales non commitées → noté, on continue)
3. Si `HEAD` a changé, comparer les fichiers modifiés
4. Si `install.sh` a été modifié → marquer pour notification (**pas** de rerun auto)

À la fin :
- Si quelque chose a changé OU échoué → `msg-send byh-dell1` avec le récap
- Si pas de changement → silence (pas de spam)
- Tout est loggé dans `/var/log/skills-autoupdate.log`

## Sécurité

- **`--ff-only` only** : refuse les pull qui nécessiteraient un merge ou rebase. Si une machine a modifié localement un fichier, le pull échoue proprement.
- **Pas de rerun automatique de install.sh** : les services tournants ne sont jamais redémarrés en silence. C'est à l'humain de relancer manuellement.
- **Source unique** : `gitea:skills/*` (tailnet-only, auth SSH ed25519 par machine). Si Gitea est compromis, tout est compromis — mais c'est déjà le modèle de menace de la flotte.

## Notifs

Quand des updates sont appliquées sur la machine `X`, byh-dell1 reçoit un message :

```
Sujet : auto-pull X: N skill(s) updated
Body  : Updates pull --ff-only OK :
        - tailnet-messaging (abc1234 → def5678)
        - claude-state-agent (xyz9999 → abc0000) — ⚠ install.sh modifié
        ...
```

byh-dell1 lui-même ne s'envoie pas de msg (juste log). Les machines sans `msg-send` installé loggent uniquement.

## Désinstallation

```bash
systemctl disable --now skills-autoupdate.timer
rm /etc/systemd/system/skills-autoupdate.{service,timer}
systemctl daemon-reload
```
