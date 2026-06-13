---
name: feedback-no-auto-authorize
description: Pas d'auto-autorisation des outils — chaque commande validée manuellement
metadata:
  type: feedback
---

**Règle** : ne pas activer "toujours autoriser" sur les outils (Bash, Edit, Write). Chaque appel doit être validé manuellement.

**Pourquoi** : c'est ce qui me permet de rester maître de ce qui se passe sur ma machine. Une IA qui a "toujours autoriser" peut faire des dégâts en quelques secondes (mauvais `rm`, mauvaise modification de config, etc.). Le coût en temps de valider chaque appel est largement compensé par la sécurité que ça apporte.

**Citation type** : « j'ai pas envie que ça casse ma prod, donc je préfère Claude Code [supervisé] aux agents en boucle ».

**Comment appliquer** :
- Garder le mode interactif (chaque outil = une validation).
- Si je propose un script de plusieurs commandes : préférer un seul `bash -c "..."` à valider, plutôt que 10 commandes individuelles qui demandent 10 validations.
- Pour les opérations destructrices (`rm`, `mv`, `git reset --hard`, `qm stop`, etc.) : double-check avec l'utilisateur avant d'agir.

**Exception** : les **MCP servers** peuvent être configurés avec une allowlist propre. C'est différent : c'est une définition de scope, pas une renonciation au contrôle.
