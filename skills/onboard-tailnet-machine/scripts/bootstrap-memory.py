#!/usr/bin/env python3
"""Creates ~/.claude/projects/-root/memory/ with a starter MEMORY.md + base reference."""
import os
import socket
import subprocess
import sys

HOME = os.path.expanduser('~')
MEM_DIR = os.path.join(HOME, '.claude/projects/-root/memory')
INDEX = os.path.join(MEM_DIR, 'MEMORY.md')


def get_tailnet_hostname():
    try:
        out = subprocess.check_output(['tailscale', 'status', '--self', '--json'],
                                       timeout=5, text=True)
        import json
        return json.loads(out)['Self'].get('HostName', socket.gethostname()).lower()
    except Exception:
        return socket.gethostname().lower()


def main():
    os.makedirs(MEM_DIR, exist_ok=True)

    if os.path.exists(INDEX):
        print(f'{INDEX} already exists, leaving as-is')
        sys.exit(0)

    host = get_tailnet_hostname()

    # Index
    with open(INDEX, 'w') as f:
        f.write('- [Tailnet basics](reference_tailnet_basics.md) — qui est Max, '
                'qui est cette machine, comment communiquer avec les autres\n')

    # Starter reference memory
    starter = os.path.join(MEM_DIR, 'reference_tailnet_basics.md')
    with open(starter, 'w') as f:
        f.write(f"""---
name: Tailnet basics — onboarding state
description: Bootstrap memory créée à l'onboarding de cette machine ({host}). À enrichir au fil du temps.
type: reference
---

## Owner

**Maxime Olivier** (`maximeolivier77@`). Communique en français, ton décontracté.
Tailnet `tail91a2f7.ts.net`, ~14 machines.

## Cette machine

`{host}` — voir `/root/CLAUDE.md` pour les détails (rôle, services, voisins).

## Coordinateurs

- **sandbox** (`100.69.73.64`) — claude central / OpenClaw "Bob"
- **byh-dell1** (`100.105.65.11`) — hyperviseur Proxmox, source de vérité tailnet
- **panels** (`100.109.129.20`) — Matrix Synapse + bot matrix-notify

## Comment communiquer avec les autres machines

- **Messages async** : taildrop avec frontmatter YAML (`to:`/`from:`/`subject:`/`priority:`/`requires_reply:`)
- **Alertes** : `matrix-notify <level> <msg>` (fonction bash, ajoutée à `~/.bashrc` à l'onboarding)
- **Code partagé** : Gitea privé `gitea.tail91a2f7.ts.net:2222`, orgs `skills`, `runbooks`, `vitrinly`

## Règles (synthèse de /root/CLAUDE.md)

1. Pas de `Read` sur fichier avec tokens — scanner d'abord avec `grep -cE '(sk-|syt_|...)'`
2. Pas de bind sur `0.0.0.0` sans raison — préférer `127.0.0.1` ou IP tailnet
3. Pas de secrets dans le transcript (commandes ni stdout)
4. SMTP → mailcow (`100.73.195.19:587`), pas d'envoi direct

## À enrichir

Au fil de tes interactions avec Max sur cette machine, ajoute des memories concrètes :
- `user_*.md` : préférences/rôle de Max sur le contexte de cette machine
- `feedback_*.md` : corrections données par Max ("ne fais pas X", "fais Y au lieu de Z")
- `project_*.md` : projets en cours avec leurs deadlines/contraintes
- `reference_*.md` : pointeurs vers external systems (Linear, Grafana, etc.)
""")

    print(f'Created {INDEX}')
    print(f'Created {starter}')


if __name__ == '__main__':
    main()
