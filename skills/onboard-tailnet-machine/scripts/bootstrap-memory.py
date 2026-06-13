#!/usr/bin/env python3
"""Creates ~/.claude/projects/-<cwd>/memory/ with a starter MEMORY.md + base reference.

Phase 1 of the kit: generic version, no specific infra refs.
"""
import os
import socket
import subprocess
import sys

HOME = os.path.expanduser('~')
# .claude/projects/ uses the cwd as a slug — replace / with -
CWD_SLUG = '-' + os.getcwd().replace('/', '-').lstrip('-')
MEM_DIR = os.path.join(HOME, '.claude/projects', CWD_SLUG, 'memory')
INDEX = os.path.join(MEM_DIR, 'MEMORY.md')


def get_hostname():
    """Try Tailscale's view of the hostname first (== identity in the tailnet),
    fall back to the system hostname."""
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

    host = get_hostname()

    # Index
    with open(INDEX, 'w') as f:
        f.write('- [Tailnet basics](reference_tailnet_basics.md) — basic context on this machine\n')

    # Starter reference memory — generic, to be enriched by the user / by Claude during bootstrap
    starter = os.path.join(MEM_DIR, 'reference_tailnet_basics.md')
    with open(starter, 'w') as f:
        f.write(f"""---
name: Tailnet basics — onboarding state
description: Bootstrap memory created at the onboarding of this machine ({host}). To enrich over time.
type: reference
---

## Owner

**(to fill in by the user)**: name, preferred language, communication tone.
Optional: tailnet domain (e.g. `your-tailnet.ts.net`), how many machines in the fleet.

## This machine

`{host}` — see `~/CLAUDE.md` (or `/root/CLAUDE.md` depending on your setup) for details on role, services, neighbours.

## Other machines in the fleet

**(to fill in by the user)** as you onboard more machines. Recommended format per machine:

- `<hostname>` — short role description, key services, hostnames or IPs

## How to communicate between machines

- **Messages and files**: `msg-send <hostname> --subject "..." --body file.md` (skill `tailnet-messaging`)
- **Shared brain** (notes, patterns, decisions): `cerveau-write` / `cerveau-search` (skill `cerveau`)
- **Secrets exchange**: `tailscale-secure-form` (skill, do not paste secrets in chat)
- **Code sharing**: Git remote of your choice (GitHub, GitLab, self-hosted Gitea, etc.)

## Default rules (from starter memory)

1. No secrets in chat — neither in commands, stdout, nor `Read`ing files containing them.
2. No bind on `0.0.0.0` without a clear reason — prefer `127.0.0.1` or the Tailscale IP.
3. Validate each tool call manually (no `always allow`).
4. Document discoveries as you go — `~/CLAUDE.md` for machine-specific, memory for user preferences, `cerveau/patterns/` for fleet-wide patterns.

## To enrich over time

As you work with this machine, add memories:

- `user_*.md`: user's role/preferences related to this machine
- `feedback_*.md`: corrections given by the user ("don't do X", "do Y instead")
- `project_*.md`: ongoing projects with their constraints/deadlines
- `reference_*.md`: pointers to external systems (issue tracker, dashboards, etc.)
""")

    print(f'✓ Wrote {INDEX} and {starter}')


if __name__ == '__main__':
    main()
