---
name: tailscale-secure-form
description: Run a private intake web form on localhost, expose it over Tailscale Serve, and collect structured submissions for agent workflows. Use when a user wants to send sensitive fields (URLs, usernames, passwords, API keys) via a temporary form instead of typing them into the chat.
---

# Tailnet Intake Form

A small Python web form, bound to `127.0.0.1`, exposed to your tailnet via
`tailscale serve`. The other end fills it in, you read the resulting JSONL file.

## ⚠ What "secure" means here (read before using)

The submission is **encrypted in transit** (via Tailscale's WireGuard tunnel) so
it can't be sniffed by anyone between the sender and you. That's the only
guarantee.

What this skill does **not** do:

- It does **not** encrypt at rest. Submissions land in a JSONL file on your
  disk in **plaintext**. If anyone else has read access to that path, they read
  your secrets.
- It does **not** auto-rotate or auto-delete. If you forget the cleanup step
  below, the file stays around forever.
- It does **not** mask submissions in process listings, journald, or shell
  history if you echo them.

Use it as **a transit channel that doesn't go through the chat transcript** —
not as a vault.

## Run the form server

```bash
python3 {baseDir}/scripts/secure_form_server.py \
  --host 127.0.0.1 \
  --port 18991 \
  --schema {baseDir}/references/example-schema.json \
  --out "$HOME/.cache/claude-fleet/intake-submissions.jsonl" \
  --title "Tailnet Intake"
```

## Expose via Tailscale Serve

```bash
tailscale serve --https=18992 http://127.0.0.1:18991
```

Then open the URL Tailscale prints in a browser **on a tailnet device**.

## Read the latest submission

```bash
tail -n 1 "$HOME/.cache/claude-fleet/intake-submissions.jsonl"
```

## Schema format

`fields` is an array of field definitions:

```json
{
  "fields": [
    {"name":"synology_url","label":"Synology URL","type":"text","required":true},
    {"name":"synology_user","label":"Synology User","type":"text","required":true},
    {"name":"synology_password","label":"Synology Password","type":"password","required":true}
  ]
}
```

Types: `text`, `password`, `textarea`, `number`, `email`.

## Cleanup (mandatory after data retrieval)

Once you've read the submission and applied the secret to its destination,
**always cleanup**. Leaving the form running + the JSONL on disk is the failure
mode here.

### 1. Stop Tailscale Serve

```bash
tailscale serve --https=18992 off
```

### 2. Stop the form server

```bash
pkill -f secure_form_server.py
```

### 3. Shred the submission file

```bash
shred -u "$HOME/.cache/claude-fleet/intake-submissions.jsonl" 2>/dev/null \
  || rm -f "$HOME/.cache/claude-fleet/intake-submissions.jsonl"
```

(`shred -u` overwrites then deletes, on filesystems that support it. Falls back
to a plain `rm` if not.)

### 4. Sanity-check

- Make sure the secret is now in its proper location (`.env`, password manager,
  service config, etc.).
- Don't echo secrets back into the chat — even after the secret has been moved,
  echoing it puts it into the conversation transcript.
