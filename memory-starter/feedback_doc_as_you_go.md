---
name: feedback-doc-as-you-go
description: Documenter au fur et à mesure — chaque découverte → CLAUDE.md, mémoire, ou skill
metadata:
  type: feedback
---

**Règle** : transformer chaque découverte non-triviale en règle écrite, immédiatement.

**Pourquoi** : sans ça, le savoir reste dans la mémoire de la session courante et disparaît dès que je perds le contexte (compaction, exit, reboot). La machine devient instable parce qu'aucune leçon ne se capitalise.

**Comment appliquer** :

- **Si c'est spécifique à cette machine** → écrire dans `/root/CLAUDE.md` (ou `~/CLAUDE.md` pour les setups user). Exemple : « ⚠️ Ne jamais relancer X sans ces deux garde-fous ».
- **Si c'est une préférence/règle générale de l'utilisateur** → écrire en mémoire (`~/.claude/projects/.../memory/feedback_*.md`).
- **Si c'est un pattern réutilisable cross-machines** → écrire dans le second cerveau partagé (`~/cerveau-flotte/patterns/...` si le skill `cerveau` est installé).
- **Si c'est du code/scripts répétitifs** → en faire un skill versionné (`~/skills/<nom>/`).

**Symptôme du problème** : « je viens de faire ça, et je ne sais pas si je l'avais déjà fait il y a 3 mois ». Si tu te poses cette question, c'est qu'il manquait un fichier de doc à un endroit.

**Tip** : « il n'y a pas d'urgence à documenter, sauf que dans 3 semaines tu auras oublié ». Documenter prend 2 minutes, redécouvrir prend 2 heures.
