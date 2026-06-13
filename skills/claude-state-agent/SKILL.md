---
name: claude-state-agent
description: Agent HTTP local installé sur chaque machine du tailnet. Expose l'état du claude code local (running, prompt, pressure PSI, transferts taildrop) et les actions (accept/reject, start/stop/restart, lecture transferts) — le tout généré LOCALEMENT sans SSH. Le daemon central central-aggregator le poll en HTTP léger. Use pour déployer l'orchestration distribuée du Stream Deck.
---

# claude-state-agent

Petit service HTTP qui tourne sur **chaque** machine du tailnet. Il connaît l'état de SON claude code (lecture directe de son tmux local, son `/proc/pressure`, son inbox tailnet-messaging) et l'expose en HTTP.

## Pourquoi

Avant : le daemon central `central-aggregator` faisait du **polling SSH** (16 machines × 4 SSH × toutes les 3s = 64 connexions SSH / 3s). Ça saturait l'hyperviseur (incident 16/05, load 97).

Maintenant : chaque machine génère son état **localement** (instantané, pas de SSH), l'expose via `GET /state`. Le daemon central fait juste des **GET HTTP légers**. Scalable, rapide, robuste.

```
Chaque machine : claude-state-agent (port 18920, bind tailnet IP)
   GET  /state                       → état local complet
   POST /action {accept_once|...}     → tmux send-keys LOCAL
   POST /claude/{start,stop,restart}
   POST /transfers/read[?transfer_id] → fait lire les taildrops au claude
   POST /transfers/{id}/archive       → marque un transfert lu

main-host : central-aggregator = agrégateur HTTP pur (plus de SSH)
```

## Install

```bash
git clone gitea:skills/claude-state-agent /root/skills/claude-state-agent
bash /root/skills/claude-state-agent/install.sh
```

`uv sync` + service systemd `claude-state-agent.service` (enable + start). Bind sur l'IP tailnet de la machine, port **18920**.

**Dépendances** : `tailnet-messaging` skill recommandé (pour le compteur de transferts exact). Sans lui, `transfers_unread` = 0.

## GET /state — format

```json
{
  "host": "panels",
  "claude_running": true,
  "tmux_session": true,
  "remote_control": true,
  "state_label": "ready_with_remote_control",
  "session_url": "https://claude.ai/code/session_xxx",
  "prompt": {
    "active": true, "type": "Bash", "subject": "rm -rf /tmp/x",
    "danger": "red", "options": ["accept_once", "accept_all", "reject"]
  },
  "pressure": {
    "io_some_avg10": 23.6, "io_full_avg10": 17.7, "cpu_some_avg10": 4.8,
    "mem_some_avg10": 0.0, "load_1min": 25.5, "stress_level": "orange"
  },
  "transfers_unread": 3,
  "transfers": [
    {"id": "20260516-...", "sender": "ia", "subject": "Rapport",
     "priority": "normal", "attachments": ["benchmark.zip"]}
  ],
  "generated_at": 1778890508.8
}
```

## Endpoints d'action

| Endpoint | Effet local |
|---|---|
| `POST /action {accept_once}` | `tmux send-keys 1 Enter` |
| `POST /action {accept_all}` | `tmux send-keys 2 Enter` |
| `POST /action {reject}` / `{esc}` | `tmux send-keys Escape` |
| `POST /action {compact_confirm}` | `tmux send-keys /compact Enter` |
| `POST /action {clear_confirm}` | `tmux send-keys /clear Enter` |
| `POST /claude/start` | `systemctl start claude-launcher.service` |
| `POST /claude/stop` | Ctrl-C ×2 + kill tmux session |
| `POST /claude/restart` | stop + start |
| `POST /transfers/read?transfer_id=X` | paste "traite le transfert X" dans le chat |
| `POST /transfers/{id}/archive` | `msg-archive {id}` direct |

## Modules

- `local_state.py` — génère l'état (tmux pane, PSI, msg-list) en local
- `parser.py` — détection état + permission prompt (partagé avec central-aggregator)
- `pressure.py` — parsing PSI + stress level (idem)
- `actions.py` — tmux send-keys local + lifecycle claude
- `agent.py` — FastAPI app

## Sécurité

Bind sur l'IP tailnet uniquement (pas `0.0.0.0`). Accessible seulement depuis le tailnet. Pas d'auth (le tailnet ACL fait le gating). Si besoin de durcir plus tard : ajouter un token partagé.
