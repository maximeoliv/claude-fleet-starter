#!/usr/bin/env python3
"""Sends an arrival broadcast (taildrop) to every active Linux machine in the tailnet."""
import json
import os
import socket
import subprocess
import sys
import tempfile
from datetime import datetime

# Hosts where we don't bother dropping (NAS without taildrop, etc.)
EXCLUDED = {'darknas', '2ndnas'}


def list_active_hosts(self_host):
    out = subprocess.check_output(['tailscale', 'status', '--json'], timeout=10, text=True)
    data = json.loads(out)
    hosts = []
    for peer in (data.get('Peer') or {}).values():
        if peer.get('Online') and peer.get('OS') == 'linux':
            h = (peer.get('HostName') or '').lower()
            if h and h not in EXCLUDED and h != self_host:
                hosts.append(h)
    return sorted(hosts)


def get_self_hostname():
    out = subprocess.check_output(['tailscale', 'status', '--self', '--json'],
                                   timeout=5, text=True)
    return json.loads(out)['Self'].get('HostName', socket.gethostname()).lower()


def get_pubkey_fingerprint():
    """Best-effort: find the ed25519 pubkey created by setup-ssh-gitea.sh."""
    home = os.path.expanduser('~')
    host = get_self_hostname()
    pubkey_path = os.path.join(home, '.ssh', f'{host}_ed25519.pub')
    if not os.path.exists(pubkey_path):
        return None
    out = subprocess.check_output(['ssh-keygen', '-lf', pubkey_path], text=True).strip()
    # format: "256 SHA256:xxx comment (ED25519)"
    parts = out.split()
    return parts[1] if len(parts) > 1 else None


def main():
    self_host = get_self_hostname()
    hosts = list_active_hosts(self_host)

    if not hosts:
        print('No active fleet hosts found, nothing to broadcast', file=sys.stderr)
        sys.exit(0)

    fp = get_pubkey_fingerprint()
    today = datetime.now().strftime('%Y-%m-%d')

    body = f"""---
to: <broadcast>
from: {self_host}
subject: Arrivée sur le tailnet — {self_host} onboardée
priority: low
requires_reply: no
---

# {self_host} onboardée le {today}

Hello,

Je viens d'être onboardée sur le tailnet via le skill `onboard-tailnet-machine`. Si tu veux pinger un truc :

- **IP tailnet** : `{subprocess.check_output(['tailscale', 'ip', '-4'], text=True).strip().splitlines()[0]}`
- **DNS** : `{self_host}.YOUR_TAILNET.ts.net`
- **Tailscale SSH** : oui (`tailscale ssh root@{self_host}`)

Mon `/root/CLAUDE.md` couvre ce qui tourne ici. Pas la peine de me demander tout de suite, je suis encore en setup.

## Pubkey SSH (pour les push Gitea)

{f'Fingerprint : `{fp}`' if fp else '(clé pas encore générée)'}

À ajouter dans Gitea UI par Max si pas déjà fait.

— {self_host}
"""

    with tempfile.NamedTemporaryFile('w', suffix='.md', delete=False,
                                       prefix=f'arrival-{self_host}-') as tmp:
        tmp.write(body)
        path = tmp.name

    sent = []
    failed = []
    for h in hosts:
        try:
            subprocess.run(['tailscale', 'file', 'cp', path, f'{h}:'],
                           check=True, timeout=15, capture_output=True)
            sent.append(h)
        except Exception as e:
            failed.append((h, str(e)[:80]))

    os.unlink(path)

    print(f'Broadcast sent to {len(sent)}/{len(hosts)} hosts:')
    for h in sent:
        print(f'  ✓ {h}')
    if failed:
        print(f'\nFailed:')
        for h, err in failed:
            print(f'  ✗ {h} — {err}')


if __name__ == '__main__':
    main()
