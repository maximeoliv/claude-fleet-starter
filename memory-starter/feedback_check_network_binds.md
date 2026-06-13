---
name: feedback-check-network-binds
description: Vérifier les binds réseau après chaque install — `ss -tlnp | grep 0.0.0.0`
metadata:
  type: feedback
---

**Règle** : après chaque `apt install`, `pip install`, `docker run`, `docker compose up`, etc., vérifier qu'aucun service ne s'est mis à écouter sur `0.0.0.0` (= tout l'internet) sans qu'on le veuille.

**Pourquoi** : beaucoup de paquets activent un service en autostart au moment de l'install, sur toutes les interfaces, sans le dire. Exemples vécus :
- `apt install chromium snap` → tire CUPS (`cupsd`) qui binde `0.0.0.0:631` → exposition CVE-2024-47176/47177 (RCE no-auth).
- `apt install libreoffice-impress` → idem, tire CUPS comme dépendance.
- `docker run` sans `-p 127.0.0.1:port:port` → port public par défaut.

**Comment appliquer** :

```bash
ss -tlnp | grep 0.0.0.0    # avant et après chaque install/setup
```

Si un nouveau port apparaît :
1. Identifier le service (`systemctl status <unit>`, `lsof -i :PORT`).
2. Décider si c'est voulu ou pas.
3. Si non voulu : soit purger le paquet (`apt purge`), soit reconfigurer le bind sur `127.0.0.1` ou sur l'IP Tailscale (`100.x.x.x`), soit `systemctl mask`.

**Variantes** :
- `ss -tunap | grep LISTEN` pour voir TCP + UDP.
- Sur Docker : `docker ps --format 'table {{.Names}}\t{{.Ports}}'` pour voir les port mappings.
- Penser à vérifier après chaque reboot aussi (services qui s'enable au boot tout seuls).
