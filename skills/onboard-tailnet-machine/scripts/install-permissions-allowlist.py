#!/usr/bin/env python3
"""Merge the fleet allow-list into ~/.claude/settings.json.

Reads `<allowlist.json>` and merges its `permissions.allow` array into the
existing settings.json (preserves `theme`, `remoteControlAtStartup`, and any
user-added allows). Idempotent: re-running just dedupes.

Pop's audit (2026-06-14) flagged that the old version auto-merged with no diff
and no confirmation. This version:
  1. Always prints the diff (what gets added).
  2. By default, asks for confirmation before writing.
  3. `--yes` skips confirmation (for the install wizard's "I trust the bundled list" path).
  4. `--dry-run` prints the diff and exits.
"""
import json
import os
import sys
from pathlib import Path

HOME = Path.home()
SETTINGS = HOME / '.claude' / 'settings.json'


def main():
    args = sys.argv[1:]
    yes = '--yes' in args
    dry_run = '--dry-run' in args
    paths = [a for a in args if not a.startswith('--')]
    if len(paths) != 1:
        print('Usage: install-permissions-allowlist.py <allowlist.json> [--yes] [--dry-run]',
              file=sys.stderr)
        sys.exit(1)

    src = Path(paths[0])
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

    existing = settings.setdefault('permissions', {}).setdefault('allow', [])
    existing_set = set(existing)
    to_add = [p for p in new_perms if p not in existing_set]

    if not to_add:
        print(f'{SETTINGS}: already in sync ({len(existing)} allow rules, nothing to add).')
        return

    print(f'About to add {len(to_add)} pre-approved permission rule(s) to {SETTINGS}:')
    for p in to_add:
        print(f'  + {p}')
    print()
    print('Each rule = a tool call Claude can run without asking you. Review carefully.')

    if dry_run:
        print('(dry-run — nothing written)')
        return

    if not yes:
        answer = input('Apply these additions? [y/N] ').strip().lower()
        if answer not in ('y', 'yes', 'o', 'oui'):
            print('Aborted — nothing written.')
            return

    merged = list(dict.fromkeys(existing + new_perms))
    settings['permissions']['allow'] = merged

    tmp = SETTINGS.with_suffix('.json.tmp')
    with tmp.open('w') as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)
        f.write('\n')
    os.chmod(tmp, 0o600)
    tmp.replace(SETTINGS)

    print(f'{SETTINGS}: {len(existing)} → {len(merged)} allow rules (+{len(to_add)}).')


if __name__ == '__main__':
    main()
