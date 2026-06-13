---
name: feedback-no-secrets
description: Jamais de secrets en clair dans le chat (mots de passe, clés API, tokens)
metadata:
  type: feedback
---

**Règle dure** : ne jamais demander à l'utilisateur de coller un mot de passe, une clé API, un token, ou tout autre secret directement dans le chat.

**Pourquoi** : tout ce qui apparaît dans le chat finit dans le transcript JSONL, peut être lu lors d'un résumé/compactage automatique, et peut survivre dans des mémoires pendant des mois. Un secret vu une fois est considéré comme compromis.

**Comment appliquer** :

- Si je dois utiliser un secret pour configurer un service : demander à l'utilisateur de l'exécuter lui-même dans une commande shell, ou utiliser un canal hors-bande (`tailscale-secure-form`, gestionnaire de mots de passe, fichier `.env` local jamais lu).
- Si je dois transmettre un secret à l'utilisateur : utiliser une URL de capability (token aléatoire dans le path, page éphémère).
- Pour configurer un service automatiquement : utiliser une variable d'environnement chargée depuis un fichier `.env` que je ne lis jamais (`grep`, `jq` direct sans `cat`).
- Si l'utilisateur colle un secret par erreur dans le chat : lui dire de le révoquer/changer immédiatement.

**Tip** : les `.env` sont par convention non lus par l'IA. Les `.json`, `.yaml`, `.conf` sont lus sans réflexion. Préférer `.env` pour tout fichier contenant des secrets.
