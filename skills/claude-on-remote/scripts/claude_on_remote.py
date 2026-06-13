#!/usr/bin/env python3
"""
claude-on-remote — pilote Claude Code sur une machine du tailnet via tmux + tailscale ssh.

Usage:
  claude-on-remote start <host> [options]
  claude-on-remote status <host>
  claude-on-remote fleet [--scan-only] [--restart-all]

Options:
  --new             Force nouvelle session (pas de resume)
  --cwd PATH        Dossier de démarrage (default: /root)
  --from-summary    Resume from summary (default: full as-is)
  --rename NAME     Nom de session claude (default: hostname machine)
  --timeout N       Timeout total du démarrage en secondes (default: 60)
"""

import argparse
import json
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# Machines exclues du fleet (configurées via env var CLAUDE_FLEET_EXCLUDED)
# Format: comma-separated hostnames, e.g.: export CLAUDE_FLEET_EXCLUDED="nas1,nas2,this-host"
# By default: excludes the current host (always — you wouldn't ssh to yourself).
import os, socket
_self = socket.gethostname().lower()
FLEET_EXCLUDED = {_self} | {
    h.strip().lower() for h in os.environ.get('CLAUDE_FLEET_EXCLUDED', '').split(',') if h.strip()
}


def ts_ssh(host, cmd, timeout=10):
    """tailscale ssh root@host cmd. Retourne (rc, stdout, stderr)."""
    try:
        proc = subprocess.run(
            ['tailscale', 'ssh', f'root@{host}', cmd],
            capture_output=True, text=True, timeout=timeout
        )
        return proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired:
        return -1, '', f'timeout after {timeout}s'


def send_keys(host, session, *keys):
    """Send keys to tmux session via SSH. Keys = chaîne(s) brute(s) ou Enter/Down/etc."""
    args = ' '.join(f"'{k}'" if not k.replace('-', '').replace('_', '').isalpha() else k for k in keys)
    return ts_ssh(host, f'tmux send-keys -t {session} {args}', timeout=8)


def capture_pane(host, session, lines=50):
    """Capture pane content as string."""
    rc, out, _ = ts_ssh(host, f'tmux capture-pane -t {session} -p -S -{lines}', timeout=8)
    return out if rc == 0 else ''


def detect_state(pane):
    """Detect Claude Code current state from pane content. Returns string label."""
    # Order matters: most specific first
    if 'Yes, I trust this folder' in pane and '❯ 1.' in pane:
        return 'trust_folder'
    if re.search(r'Resume session', pane, re.IGNORECASE) and 'Search' in pane:
        return 'resume_picker'
    if 'Resume from summary' in pane and 'Resume full session as-is' in pane:
        return 'resume_mode_choice'
    if 'Browser didn' in pane or 'Paste code here' in pane:
        return 'oauth_pending'
    # Footer signals — exact wording observed in claude code v2026.05
    if '/remote-control is active' in pane:
        return 'ready_with_remote_control'
    if 'control this session from your phone' in pane:
        return 'ready_no_remote_control'
    # Tâche en cours (compact, tool call, agent…)
    if 'esc to interrupt' in pane:
        return 'busy'
    # Idle prompt visible mais sans footer reconnu (pane scrollée hors footer)
    if re.search(r'─ [a-z0-9-]+ ─', pane) and '❯' in pane:
        return 'ready_unknown_remote_control'
    if 'Welcome to Claude Code' in pane:
        return 'starting'
    return 'unknown'


def session_exists(host, session):
    rc, _, _ = ts_ssh(host, f'tmux has-session -t {session} 2>/dev/null')
    return rc == 0


def create_session(host, session, cwd='/root'):
    """Create detached tmux session."""
    rc, out, err = ts_ssh(
        host,
        f'cd {cwd} && tmux new-session -d -s {session} -x 200 -y 50',
        timeout=8,
    )
    return rc == 0


def get_state(host, session='claude', timeout=8):
    """Returns dict with tmux/claude/remote_control booleans + label."""
    state = {
        'host': host,
        'session': session,
        'tmux_session': False,
        'claude_running': False,
        'remote_control': False,
        'state_label': None,
        'error': None,
    }
    rc, out, err = ts_ssh(host, "tmux list-sessions -F '#{session_name}'", timeout=timeout)
    if rc < 0:
        state['error'] = err
        return state
    sessions = out.strip().split('\n') if out.strip() else []
    if session not in sessions:
        return state
    state['tmux_session'] = True

    pane = capture_pane(host, session, lines=20)
    label = detect_state(pane)
    state['state_label'] = label
    if label in ('ready_with_remote_control', 'ready_no_remote_control',
                 'ready_unknown_remote_control', 'resume_picker',
                 'resume_mode_choice', 'trust_folder', 'starting',
                 'oauth_pending', 'busy'):
        state['claude_running'] = True
    if label == 'ready_with_remote_control':
        state['remote_control'] = True
    return state


def start_claude(host, cwd='/root', resume=True, from_summary=True, rename=None,
                 max_wait_seconds=60, verbose=True, session='claude'):
    """Démarre claude code sur host avec /remote-control + /rename."""
    # Convention: tmux session locale = 'claude' (nom local sur la machine).
    # Le rename côté UI claude (visible depuis claude.ai/code) = hostname.
    rename = rename or host
    log = []

    def step(msg):
        log.append(f'[{host}] {msg}')
        if verbose:
            print(log[-1], flush=True)

    # 1. Tmux session
    if not session_exists(host, session):
        if not create_session(host, session, cwd):
            log.append(f'[{host}] FAIL create tmux session')
            return {'host': host, 'success': False, 'log': log}
        step(f"tmux session '{session}' created in {cwd}")
        time.sleep(1)
    else:
        step(f"tmux session '{session}' already exists")

    # 2. Check current pane state
    pane = capture_pane(host, session, lines=20)
    initial_label = detect_state(pane)
    step(f'initial state: {initial_label}')

    if initial_label == 'ready_with_remote_control':
        step('already running with remote-control — nothing to do')
        return {'host': host, 'success': True, 'log': log}

    # 3. If empty/unknown shell prompt, launch claude
    if initial_label == 'unknown':
        cmd = 'claude -r' if resume else 'claude'
        ts_ssh(host, f"tmux send-keys -t {session} '{cmd}' Enter", timeout=5)
        step(f'sent: {cmd}')
        time.sleep(4)

    # 4. State machine loop
    deadline = time.time() + max_wait_seconds
    last_label = None
    stuck_count = 0

    while time.time() < deadline:
        pane = capture_pane(host, session, lines=50)
        label = detect_state(pane)

        if label == last_label:
            stuck_count += 1
            # 'busy' = tâche claude en cours (compact, agent, tool…) → patience
            stuck_threshold = 60 if label == 'busy' else 5
            if stuck_count > stuck_threshold:
                step(f'STUCK in state {label} after {stuck_count} polls — abort')
                return {'host': host, 'success': False, 'log': log, 'final_state': label}
        else:
            stuck_count = 0
            last_label = label
            step(f'state: {label}')

        if label == 'busy':
            time.sleep(3)
            continue

        if label == 'trust_folder':
            ts_ssh(host, f'tmux send-keys -t {session} Enter', timeout=5)
            time.sleep(2)
            continue

        if label == 'resume_picker':
            # Le chat avec le nom de la machine devrait être sélectionné par défaut.
            # On envoie juste Enter — claude resume picker filtre par cwd current.
            ts_ssh(host, f'tmux send-keys -t {session} Enter', timeout=5)
            time.sleep(3)
            continue

        if label == 'resume_mode_choice':
            if from_summary:
                # Option 1 (default selected) — just Enter
                ts_ssh(host, f'tmux send-keys -t {session} Enter', timeout=5)
            else:
                # Option 2 (full session as-is) — Down then Enter
                ts_ssh(host, f'tmux send-keys -t {session} Down Enter', timeout=5)
            time.sleep(4)
            continue

        if label == 'oauth_pending':
            step('OAuth pending — manual user action required (open URL in browser)')
            return {'host': host, 'success': False, 'log': log,
                    'final_state': label, 'note': 'oauth_pending'}

        if label in ('ready_no_remote_control', 'ready_unknown_remote_control'):
            ts_ssh(host, f"tmux send-keys -t {session} '/remote-control' Enter", timeout=5)
            step(f'sent /remote-control (from {label})')
            time.sleep(4)
            continue

        if label == 'ready_with_remote_control':
            step('Remote Control active ✓')
            # Optionally rename if not already (only relevant for new sessions)
            if rename and not resume:
                ts_ssh(host, f"tmux send-keys -t {session} '/rename {rename}' Enter", timeout=5)
                step(f'sent /rename {rename}')
                time.sleep(2)
            return {'host': host, 'success': True, 'log': log, 'final_state': label}

        time.sleep(2)

    step(f'TIMEOUT after {max_wait_seconds}s, last state: {last_label}')
    return {'host': host, 'success': False, 'log': log, 'final_state': last_label}


def list_tailnet_hosts():
    """Liste les hostnames Linux online (hors EXCLUDED)."""
    proc = subprocess.run(['tailscale', 'status', '--json'],
                          capture_output=True, text=True, timeout=10)
    data = json.loads(proc.stdout)
    hosts = []
    for k, peer in (data.get('Peer') or {}).items():
        if peer.get('Online') and peer.get('OS') == 'linux':
            host = (peer.get('HostName') or '').lower()
            if host and host not in FLEET_EXCLUDED:
                hosts.append(host)
    return sorted(hosts)


def fleet_status(parallel=8):
    hosts = list_tailnet_hosts()
    results = []
    with ThreadPoolExecutor(max_workers=parallel) as executor:
        future_to_host = {executor.submit(get_state, h): h for h in hosts}
        for future in as_completed(future_to_host):
            results.append(future.result())
    return sorted(results, key=lambda s: s['host'])


def cmd_start(args):
    result = start_claude(
        args.host,
        cwd=args.cwd,
        resume=not args.new,
        from_summary=not args.full_as_is,
        rename=args.rename,
        max_wait_seconds=args.timeout,
        verbose=True,
    )
    print()
    print(f"Result: {'OK' if result['success'] else 'FAIL'}")
    if not result['success']:
        print(f"Final state: {result.get('final_state', '?')}")
    sys.exit(0 if result['success'] else 1)


def cmd_status(args):
    state = get_state(args.host)
    print(json.dumps(state, indent=2, ensure_ascii=False))
    sys.exit(0 if state['remote_control'] else 1)


def cmd_fleet(args):
    print('Scanning fleet...')
    states = fleet_status()
    print()
    print(f"{'Host':<15} {'tmux':<6} {'claude':<8} {'r-ctrl':<7} {'state':<25} {'note'}")
    print('-' * 80)
    to_start = []
    for s in states:
        tm = '✓' if s['tmux_session'] else '✗'
        cl = '✓' if s['claude_running'] else '✗'
        rc = '✓' if s['remote_control'] else '✗'
        note = s.get('error') or ''
        label = s.get('state_label') or '-'
        print(f"{s['host']:<15} {tm:<6} {cl:<8} {rc:<7} {label:<25} {note}")
        if (not s['remote_control'] and not s['error']) or args.restart_all:
            to_start.append(s['host'])

    if args.scan_only:
        return

    if not to_start:
        print('\nAll machines OK, nothing to do.')
        return

    print(f"\nStarting on: {', '.join(to_start)}")
    with ThreadPoolExecutor(max_workers=4) as executor:
        future_to_host = {
            executor.submit(start_claude, h, verbose=False): h
            for h in to_start
        }
        for future in as_completed(future_to_host):
            result = future.result()
            mark = '✓' if result['success'] else '✗'
            note = ''
            if not result['success']:
                note = f" — final: {result.get('final_state', '?')}"
            print(f"  {mark} {result['host']}{note}")


def main():
    parser = argparse.ArgumentParser(description='Pilote Claude Code remote via tmux+SSH')
    sub = parser.add_subparsers(dest='cmd', required=True)

    sp = sub.add_parser('start', help='Start claude on host')
    sp.add_argument('host')
    sp.add_argument('--new', action='store_true', help='Force new session (no resume)')
    sp.add_argument('--cwd', default='/root', help='Working directory (default: /root)')
    sp.add_argument('--full-as-is', action='store_true',
                    help='Resume full session as-is (DANGEREUX: rejoue le dernier input). '
                         'Default: from summary (safe)')
    sp.add_argument('--rename', default=None,
                    help='Session name (default: hostname). Used only with --new')
    sp.add_argument('--timeout', type=int, default=60, help='Total timeout (s)')
    sp.set_defaults(func=cmd_start)

    sp = sub.add_parser('status', help='Check claude state on host')
    sp.add_argument('host')
    sp.set_defaults(func=cmd_status)

    sp = sub.add_parser('fleet', help='Scan all machines + start the down ones')
    sp.add_argument('--scan-only', action='store_true', help='Just scan, do not start')
    sp.add_argument('--restart-all', action='store_true',
                    help='Restart all machines, even those already running')
    sp.set_defaults(func=cmd_fleet)

    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
