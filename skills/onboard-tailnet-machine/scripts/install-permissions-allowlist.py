#!/usr/bin/env python3
"""Merges the fleet allow-list into ~/.claude/settings.json on this machine.

Reads {baseDir}/data/permissions-allowlist.json and merges the `permissions.allow`
array into the existing settings.json (preserves theme, remoteControlAtStartup,
and any user-added allows). Idempotent: re-running just dedupes.
"""
import json
import os
import sys
from pathlib import Path

HOME = Path.home()
SETTINGS = HOME / '.claude' / 'settings.json'


def main():
    if len(sys.argv) != 2:
        print('Usage: install-permissions-allowlist.py <path-to-allowlist.json>',
              file=sys.stderr)
        sys.exit(1)

    src = Path(sys.argv[1])
    if not src.exists():
        print(f'ERROR: source allowlist not found: {src}', file=sys.stderr)
        sys.exit(1)

    with src.open() as f:
        new_perms = json.load(f).get('permissions', {}).get('allow', [])

    if SETTINGS.exists():
        with SETTINGS.open() as f:
            settings = json.load(f)
    else:
        SETTINGS.parent.mkdir(parents=True, exist_ok=True)
        settings = {}

    existing_perms = settings.setdefault('permissions', {}).setdefault('allow', [])

    before = len(existing_perms)
    merged = list(dict.fromkeys(existing_perms + new_perms))  # preserve order, dedupe
    settings['permissions']['allow'] = merged
    after = len(merged)

    tmp = SETTINGS.with_suffix('.json.tmp')
    with tmp.open('w') as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)
        f.write('\n')
    os.chmod(tmp, 0o600)
    tmp.replace(SETTINGS)

    print(f'{SETTINGS}: {before} → {after} allow rules ({after - before} added)')


if __name__ == '__main__':
    main()
