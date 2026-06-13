---
name: tailscale-secure-form
description: Create and run a private credential/intake web form on localhost, expose it over Tailscale Serve, and collect structured submissions for agent workflows. Use when a user wants to send sensitive fields (URLs, usernames, passwords, API keys) via a temporary form instead of chat.
---

# Tailscale Secure Form

Create a temporary local form, expose it on tailnet, collect submissions in JSON.

## Run server

```bash
python3 {baseDir}/scripts/secure_form_server.py \
  --host 127.0.0.1 \
  --port 18991 \
  --schema {baseDir}/references/example-schema.json \
  --out /root/.openclaw/workspace/tmp/secure-form/submissions.jsonl \
  --title "Secure Intake"
```

## Expose via Tailscale Serve

```bash
tailscale serve --https=18992 http://127.0.0.1:18991
```

Then open your tailnet URL shown by Tailscale.

## Read latest submission

```bash
tail -n 1 /root/.openclaw/workspace/tmp/secure-form/submissions.jsonl
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

## Security notes

- Keep server bound to `127.0.0.1`.
- Use Tailscale Serve for private access only.
- Submissions are stored locally in JSONL; move/delete after import.
- Do not echo secrets back to chat.

## Cleanup (after data retrieval)

Once the user has submitted the form and you've extracted the data, **always cleanup** to prevent leaving sensitive endpoints or files exposed:

### 1. Stop Tailscale Serve
```bash
tailscale serve --https=<port> off
```
Example: `tailscale serve --https=18992 off`

### 2. Stop the form server
```bash
pkill -f secure_form_server.py
```

### 3. Remove temporary files
```bash
rm -rf /root/.openclaw/workspace/tmp/secure-form
```

### 4. Secure sensitive data (optional but recommended)
- Move the submission file out of `/tmp` if you need to keep it
- Check logs don't contain secrets: `grep -r "sk-" /root/.openclaw/logs/ 2>/dev/null`
- Delete the `.jsonl` file once the secret is applied to config
