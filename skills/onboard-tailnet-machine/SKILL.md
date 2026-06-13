---
name: onboard-tailnet-machine
description: Onboard a freshly-installed Linux machine into Max's tailnet ecosystem. Generates CLAUDE.md, sets up matrix-notify, configures SSH access to Gitea, bootstraps the agent memory directory, and broadcasts the new machine's arrival to the fleet. Use when a new machine just joined the tailnet and has no context yet (no CLAUDE.md, no skills, no SSH config to Gitea).
---

# Onboard tailnet machine

Bring a brand-new machine into the tailnet ecosystem of Max (`maximeolivier77@`, tailnet `tail91a2f7.ts.net`).

The skill runs **locally on the new machine** (the claude code that's already authenticated there invokes it). It does NOT run from byh-dell1 — each machine onboards itself.

## Prereqs

The machine must already have:
- `tailscale` connected (visible in `tailscale status` from any other machine)
- `tailscale set --ssh` activated (so other agents can reach it via tailscale ssh)
- `claude` installed and authenticated (otherwise this skill couldn't be invoked)
- This skill copied locally (e.g. via `tailscale file cp` from byh-dell1, or git clone once SSH-to-Gitea is set up — chicken-and-egg, see below)

## 5 phases

Run them in order. Each is idempotent: re-running won't break anything.

> ⚠️ Phase 5 (permissions allow-list) **doit idéalement être faite AVANT le premier `claude` run** sur la machine, sinon les nouvelles permissions ne sont pas appliquées tant que claude code n'a pas été redémarré.

### Phase 1 — Generate `/root/CLAUDE.md`

```bash
bash {baseDir}/scripts/detect-machine.sh > /tmp/machine.json
python3 {baseDir}/scripts/render-claude-md.py /tmp/machine.json {baseDir}/templates/CLAUDE.md.j2 > /root/CLAUDE.md
```

Then **edit** `/root/CLAUDE.md` manually or via claude to:
- Fill in the **rôle** of the machine (what runs on it, why it exists)
- List public-facing services (vhosts, ports exposed)
- Note any quirks specific to this machine

The template has a "Conventions tailnet" section that's identical across machines — leave it as-is.

### Phase 2 — Install `matrix-notify` for inter-machine alerts

```bash
bash {baseDir}/scripts/install-matrix-notify.sh
```

Adds a bash function `matrix-notify` to `~/.bashrc` that pipes alerts to the Matrix room `alerts-tailnet` via `panels` (which has the bot token). The function tags the message with this machine's hostname automatically.

Test:
```bash
source ~/.bashrc
matrix-notify info "Onboarding test from $(hostname)"
```
Max should see the message in Matrix.

### Phase 3 — SSH config + Gitea key

```bash
bash {baseDir}/scripts/setup-ssh-gitea.sh
```

This generates an `ed25519` key at `~/.ssh/<hostname>_ed25519`, writes `~/.ssh/config` with the `gitea` alias (HostName `gitea.tail91a2f7.ts.net`, port 2222, user git), and prints the **public key** to stdout.

**Manual step** (the script can't do this without a Gitea API token): copy the printed pubkey into Gitea UI → User Settings → SSH/GPG Keys → Add Key. Title it `<hostname> root`.

Test:
```bash
ssh -T gitea
# Expected: "Hi there, <gitea_user>! You've successfully authenticated..."
```

### Phase 4 — Memory bootstrap + arrival broadcast

```bash
python3 {baseDir}/scripts/bootstrap-memory.py
python3 {baseDir}/scripts/broadcast-arrival.py
```

- `bootstrap-memory.py` creates `~/.claude/projects/-root/memory/` with a `MEMORY.md` index pointing to a single starter file `reference_tailnet_basics.md` (machines, conventions, sec rules).
- `broadcast-arrival.py` sends a taildrop to every active fleet machine announcing the new machine + its role + Gitea pubkey fingerprint.

### Phase 5 — Permissions allow-list (anti-prompts-fatigue)

```bash
python3 {baseDir}/scripts/install-permissions-allowlist.py {baseDir}/data/permissions-allowlist.json
```

Merges 66 conservative read-only permission rules into `~/.claude/settings.json` so claude code stops prompting for every `Read`/`Bash` of safe operations (ls, cat, grep, tailscale, docker inspect, systemctl status, etc.). Destructive commands (rm, mv, docker stop, systemctl restart, write outside /tmp) still prompt — the allow-list is intentionally conservative.

**Why**: a known limitation of the remote-control feature (claude.ai/code) is that permission prompts don't appear in the web UI, so the user can't approve them remotely. The allow-list bypasses prompts for safe operations entirely.

⚠️ **Restart claude code** for the new settings to take effect. If claude is currently running and you can't restart it (e.g. it has unfinished work), the allow-list will only apply on the next launch.

If you add a custom command pattern Max uses often, append it to `data/permissions-allowlist.json`, then re-run this script on each affected machine.

## Chicken-and-egg: how does the skill get to the new machine?

Before SSH-to-Gitea is configured, the machine can't `git clone` the skill from Gitea. So bootstrap goes via **taildrop**:

```bash
# from byh-dell1 (or any onboarded machine):
cd /root/skills && tar czf /tmp/onboard.tgz onboard-tailnet-machine/
tailscale file cp /tmp/onboard.tgz <new-host>:

# on the new machine:
mkdir -p /root/skills && cd /root/skills
tailscale file get .
tar xzf onboard.tgz
rm onboard.tgz
```

Then invoke this skill from claude on the new machine.

## Conventions reminder (also in CLAUDE.md template)

- Inter-agent messages: taildrop with YAML frontmatter (`to:`, `from:`, `subject:`, `priority:`, `requires_reply:`)
- Sandbox = central coordinator
- Gitea (`gitea.tail91a2f7.ts.net`) = private repos (skills/runbooks/etc.)
- mailcow = SMTP relay for tailnet apps
- Never bind on `0.0.0.0` — use `127.0.0.1` or the machine's tailnet IP
- Never `Read` a file with secrets — scan first with `grep -cE '(sk-|syt_|AIza|Bearer|password|secret)'` then extract via `jq -r`
