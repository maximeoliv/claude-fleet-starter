---
name: claude-launcher
description: Auto-launches the local claude code in a persistent tmux session at boot, with remote-control and the most recent conversation auto-resumed. Installs as a systemd service on the local machine. Use after onboarding to make claude survive reboots.
---

# Claude launcher

Boot → tmux session `claude` → `claude --remote-control <hostname> --continue` → ready.

Survives:
- Reboots (systemd service)
- SSH disconnects (tmux detaches)
- Claude crashes (tmux session stays, you can re-launch)

## Install on this machine

```bash
bash {baseDir}/scripts/install.sh
```

This:
1. Copies `claude-launcher.service` to `/etc/systemd/system/`
2. Runs `systemctl daemon-reload && systemctl enable claude-launcher.service`
3. Verifies the service is enabled (does NOT start it now — it'll fire on the next reboot)

## Test without rebooting

```bash
# Manually trigger the service (simulates what happens at boot)
systemctl start claude-launcher.service

# Check tmux session was created
tmux list-sessions  # should show "claude"

# Attach to see what happened
tmux attach -t claude
```

## Verify boot behavior (real reboot)

```bash
reboot
# wait ~30s, then from another machine:
tailscale ssh root@<this-host> "tmux list-sessions"  # should show "claude"
```

The new claude.ai/code URL will appear in the freshly-booted session — it'll be a NEW remote-control session each boot (different URL each time), but the conversation continues from where it was.

## Uninstall

```bash
systemctl disable claude-launcher.service
rm /etc/systemd/system/claude-launcher.service
systemctl daemon-reload
rm -f /usr/local/bin/claude-fork
```

## Forker une session vers un autre cwd (`claude-fork`)

`claude-fork` est un wrapper qui automatise le fork d'une session Claude Code existante dans une nouvelle tmux session. Utile pour dédier un projet long à sa propre session sans interrompre la session principale (ex : projet `deck-ia` forké depuis `claude` machine-wide).

### Usage

```bash
claude-fork <source> <new-name> [--cwd <path>] [--remote-control <alias>] [--no-prompt]
```

- `<source>` : session source. Soit son nom/slug (ex `claude`, `deck-ia`), soit son UUID (ex `afe181e2-...`).
- `<new-name>` : nom de la nouvelle session. Utilisé comme nom tmux, `claude --name`, et alias Remote Control par défaut.
- `--cwd <path>` : répertoire de travail conceptuel de la session forkée (créé si absent). Par défaut, le même que le project de la source.
- `--remote-control <alias>` : alias Remote Control distinct (par défaut = `<new-name>`).
- `--no-prompt` : ne pas envoyer le prompt d'orientation automatique vers `--cwd` (drive manuel).

### Exemples

```bash
# Forker la session principale vers un projet dédié, avec orientation auto vers /root/projet-deck-ia
claude-fork claude deck-ia --cwd /root/projet-deck-ia

# Forker par UUID, même cwd que la source
claude-fork afe181e2-5ed3-4bf7-a4eb-13e9bad7eba8 experiment

# Forker sans prompt automatique (utile pour drive manuel)
claude-fork claude my-sandbox --cwd /root/sandbox --no-prompt
```

### Méthode A vs Méthode B (pourquoi le wrapper applique A)

Claude Code organise ses sessions **par project directory** : `/root` → `~/.claude/projects/-root/`, `/root/projet-deck-ia` → `~/.claude/projects/-root-projet-deck-ia/`. `claude --resume <id>` cherche uniquement dans le project dérivé du cwd au launch, pas globalement. Et `--fork-session` crée le fork dans le project courant. Conséquence : pas de méthode officielle pour forker vers un nouveau cwd.

**Méthode A (implémentée)** : on lance tmux dans le project dir de la source (pour que `--resume` trouve la session), puis on envoie un prompt d'orientation pour que la session forkée travaille en chemins absolus dans `--cwd`. Le project Claude Code reste partagé avec la source. Cosmétique : le slug et le Remote Control alias sont uniques, donc la session est identifiable côté monitoring (`claude-state-agent`, `streamdeck-bridge`) et messagerie (`msg-send host:slug`).

**Méthode B (non implémentée)** : copier le jsonl de la session dans le project dir cible puis lancer depuis ce cwd. Théoriquement plus propre (vrai isolation project) mais non documentée et non testée. Les champs `cwd` historiques de chaque entry du jsonl ne sont pas mis à jour, risque de comportements surprenants. Si quelqu'un valide en sandbox, on pourra l'ajouter au wrapper sous `--method B`.

### Prérequis

- `claude-state-agent` actif sur cette machine (port 18920) : utilisé par `claude-fork` pour découvrir les sessions existantes via `/sessions/discover`.
- `tmux`, `claude` (CLI), `python3` dans le PATH.

## Architecture decisions (V1)

- **One tmux session `claude` per machine** (not multi-session) — covers 95% of cases. Multi-session is V2.
- **`claude -c --remote-control <hostname>`** — combines auto-resume of last conversation in `/root` + auto-activation of remote-control. The hostname becomes the remote-control session name (visible in claude.ai/code).
- **Fallback to fresh start**: if `claude -c` fails (e.g. no prior conversation in `/root`), the wrapper drops to `claude --remote-control <hostname>` (new session).
- **No keystroke automation**: trust folder must be already trusted (it's mémorisé in `~/.claude.json` after first use). If you re-onboard a fresh `/root`, run `claude -c --remote-control <hostname>` once interactively to trust.

## Limitations

- **First-time boot on a fresh machine**: trust folder won't be auto-accepted. Run claude once manually to trust before relying on the service.
- **OAuth pending**: if claude's OAuth token expires (rare with Claude Pro/Max subscription), the service silently fails — no automatic re-auth. You'll see it on the next interactive session.
- **No multi-session restore**: if you had 3 claude conversations in different cwd's, only the one in `/root` is auto-resumed. Others must be relaunched manually (or upgrade to V2 multi-session).
