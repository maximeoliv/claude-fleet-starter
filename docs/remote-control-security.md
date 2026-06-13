# Remote Control — points de sécurité à comprendre

Le **Remote Control** (RC) est la fonctionnalité de Claude Code qui te permet de piloter une session Claude Code à distance, depuis :

- L'app mobile Claude (iOS / Android)
- claude.ai/code dans un navigateur

C'est très pratique : tu peux suivre ce que fait ton Claude Code sur ton serveur depuis ton téléphone, lui envoyer de nouveaux prompts, et même valider des appels d'outils à distance.

**Mais ça a des implications de sécurité que tu dois comprendre avant de l'activer.**

---

## ⚠ Point 1 : qui partage l'accès ?

Le Remote Control est lié à **ton compte claude.ai**, pas à un mot de passe spécifique au RC.

**Concrètement** : si quelqu'un d'autre a accès à ton compte claude.ai (= ton email + mot de passe + 2FA), il peut **piloter ton Claude Code à distance**, exécuter des commandes sur ta machine, lire tes fichiers, etc.

**Cas typiques où ça peut poser problème** :

- Tu partages ton compte claude.ai avec un membre de la famille / ton/ta partenaire.
- Tu partages ton compte avec ton équipe pour économiser une licence.
- Quelqu'un connaît ton mot de passe parce qu'il est utilisé ailleurs (réutilisation de mot de passe = mauvaise idée en général).

**Recommandations** :

- N'active le RC que si tu es **le seul à utiliser ton compte claude.ai**.
- Active **l'authentification à deux facteurs (2FA)** sur claude.ai.
- Si tu partages un compte d'équipe : sache que **tout le monde dans l'équipe peut piloter tes machines**. Décide si c'est OK ou non.

---

## ⚠ Point 2 : qui voit ton code et tes données ?

Avec le RC activé, l'app Claude (mobile / web) affiche en temps réel :

- Le contenu de ta session Claude Code
- Les commandes exécutées
- Les fichiers lus ou modifiés
- Tes prompts et les réponses

**Donc** : si quelqu'un d'autre accède à ton compte (point 1), il voit aussi **tout ce que tu fais avec Claude Code**.

**Recommandation** : si tu bosses sur du code confidentiel (client, projet privé, etc.), sois vigilant sur qui a accès à ton compte claude.ai.

---

## ⚠ Point 3 : autorisation des outils à distance

Si tu actives le RC + l'auto-autorisation des outils (= « toujours autoriser »), une personne qui contrôle à distance peut **lancer des commandes Bash sur ta machine** sans que tu valides quoi que ce soit.

**Recommandation par défaut** : garde l'auto-autorisation **désactivée** (= chaque appel d'outil = une validation manuelle). C'est la convention par défaut du kit.

Voir aussi : [`memory-starter/feedback_no_auto_authorize.md`](../memory-starter/feedback_no_auto_authorize.md)

---

## ⚠ Point 4 : ce qui n'est PAS un risque

Pour rassurer :

- Le RC **ne donne pas accès à ton compte cloud Anthropic en lui-même** (tes paramètres facturation, billing, etc.). C'est juste un canal d'interaction temps réel avec la session Claude Code qui tourne sur ta machine.
- Le RC ne contourne **pas** les permissions de l'OS : Claude Code tourne avec les droits de l'utilisateur qui l'a lancé. Si tu lances Claude Code en `user`, il ne pourra pas `sudo` sans validation.
- Si tu fermes ta session Claude Code, le RC est coupé.

---

## Comment désactiver le RC plus tard

Si tu as activé le RC à l'installation et que tu veux le couper :

1. Dans ta session Claude Code, tape la commande :
   ```
   /remote-control
   ```
   → Claude Code te montre l'état actuel et te permet de le désactiver.

2. Ou : tue la session tmux qui héberge Claude Code :
   ```bash
   tmux kill-session -t claude
   ```

3. Et pour empêcher le démarrage automatique au prochain reboot, désactive le service :
   ```bash
   systemctl --user disable claude-launcher
   # ou (selon ton setup)
   systemctl disable claude-launcher
   ```

---

## Résumé

| Situation | Activer le RC ? |
|---|---|
| Compte claude.ai personnel, tu es seul à l'utiliser, 2FA activé | ✅ Oui, super pratique |
| Compte partagé avec un membre de confiance (conjoint, etc.) | 🟡 OK si tu acceptes qu'il puisse contrôler tes machines |
| Compte partagé avec une équipe | 🟡 OK si l'équipe entière a légitimement accès aux machines |
| Compte partagé avec qqn que tu ne connais pas bien | ❌ Non |
| Tu bosses sur du code/donnees client ultra-sensibles | 🟡 Réfléchis-y, peut-être à éviter |

Tu peux toujours **changer d'avis plus tard**. Active maintenant, désactive après. Pas grave.
