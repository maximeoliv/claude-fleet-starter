# Prompt de test à donner à Claude Code

Si tu testes le `claude-fleet-starter` pour Maxime, copie-colle **tout** le bloc ci-dessous dans ton Claude Code (ou ouvre une nouvelle session et colle). L'IA va suivre les instructions et te guidera.

---

## 📋 Prompt à coller

```
Salut. Tu vas m'aider à tester un kit d'installation de Claude Code multi-machine qui s'appelle `claude-fleet-starter`. C'est un projet open source que Maxime (mon ami) développe — il l'a poussé sur GitHub : https://github.com/maximeoliv/claude-fleet-starter

Le but de ce test : **valider l'expérience utilisateur** du kit en tant que personne non-experte. Tu dois jouer le rôle d'un utilisateur intermédiaire qui découvre le kit pour la première fois.

## Règles du jeu

1. **Ne fais PAS tout en parallèle / en automatique** — fais les choses séquentiellement, comme un humain le ferait. Lance une commande, observe ce qui s'affiche, puis passe à la suivante.

2. **Note tout ce qui pose problème** : commande qui échoue, message d'erreur cryptique, doc pas claire, étape sautée, dépendance manquante, jargon non expliqué, formulation maladroite, faute de français, etc. Sois honnête, c'est exactement pour ça qu'on te teste.

3. **Évalue chaque étape sur 5 critères** (note de 1 à 5) :
   - Clarté des instructions
   - Simplicité d'exécution
   - Confiance que ça va marcher
   - Qualité des messages d'erreur (si erreurs)
   - Cohérence avec ce qu'attendrait un utilisateur normal

4. **Tu peux interrompre** le test si tu rencontres un problème bloquant. Note-le et passe à la suite si possible.

## Environnement de test

⚠️ **N'installe PAS sur une machine en production** ou avec des données importantes. Si tu n'as pas de machine de test sous la main :
- Soit tu fais un container Docker propre (`docker run -it --rm debian:12 bash`) et tu tests dedans
- Soit tu fais une VM (VirtualBox / VMware / Proxmox / etc.)
- Soit tu fais sur un Synology DSM de test (pas le NAS principal de l'utilisateur)

Demande à l'utilisateur sur quel type de machine il veut tester avant de commencer.

## Étapes du test

### Étape 1 — Lire le README
Va lire le README.md du repo : https://github.com/maximeoliv/claude-fleet-starter/blob/main/README.md

Note tes premières impressions :
- Est-ce qu'on comprend rapidement ce que fait le kit ?
- Est-ce qu'on a envie de l'installer ?
- Qu'est-ce qui manque dans le README ?

### Étape 2 — Lancer l'install
Selon le choix de machine de test, lance :

```bash
# Sur Debian/Ubuntu/Pop/Synology DSM :
curl -fsSL https://raw.githubusercontent.com/maximeoliv/claude-fleet-starter/main/install.sh -o /tmp/install.sh
bash /tmp/install.sh
```

Suis le wizard interactif. À chaque question :
- Note la question (texte exact)
- Note ce que tu réponds et pourquoi
- Note la réaction du script
- Si tu hésites sur une question, note ça aussi

### Étape 3 — Tester quelques commandes après install

Une fois l'install terminée :

```bash
# La messagerie inter-machine
msg-send --help
msg-list

# Le second cerveau
cerveau-search "test"
cerveau-list

# L'agent d'état local
curl -s http://localhost:18920/health 2>&1 | head -3

# Le launcher
ls ~/.claude-fleet-starter/
```

Note ce qui marche, ce qui ne marche pas.

### Étape 4 — Lire la sécurité Remote Control
Lis `docs/remote-control-security.md` :
- Est-ce que ça t'a fait comprendre les enjeux ?
- Est-ce qu'il y a des points qu'on devrait ajouter ?

### Étape 5 — Désinstaller
Tente de désinstaller le kit pour voir si la procédure marche / est documentée.

## Format du rapport final

À la fin du test, génère un rapport markdown avec cette structure :

```markdown
# Rapport de test claude-fleet-starter

**Testeur** : (nom de l'utilisateur)
**Date** : (date)
**Machine de test** : (description courte)
**Durée totale du test** : ~X minutes

## Score global : X/5

## Impressions initiales (lecture du README)
[ce que tu notes]

## Wizard d'install
### Question 1 — ...
- Question exacte : ...
- Ma réponse : ...
- Note : X/5 — clarté / simplicité / confiance / messages / cohérence
- Commentaire : ...

[continuer pour chaque question]

## Tests post-install
[ce qui marche / ce qui ne marche pas]

## Documentation
[évaluation des docs lus]

## Bugs identifiés
[liste numérotée avec criticité bloquante/sévère/mineure]

## Suggestions d'amélioration
[liste numérotée]

## Verdict
- Est-ce que le kit est prêt pour des utilisateurs non-techniques ? Oui / Non / Avec ces fixes : ...
- Est-ce que tu le recommanderais à un ami ? Oui / Non / Avec réserve
```

## Comment envoyer le rapport

Une fois le rapport prêt, tu peux :
- **Si tu as Tailscale + tailnet-messaging installé** (= le kit a marché) : `msg-send maximeolivier-machine --subject "Rapport test" --body /tmp/rapport.md`
- **Sinon** : copie-colle le rapport dans le chat avec ton humain, il le transmettra à Maxime.

## Important

Sois honnête. Si le kit est mal foutu, dis-le. C'est précisément pour ça qu'on teste avant la version publique. Maxime préfère un retour direct qui pique à un retour poli qui ne sert à rien.

Quand tu es prêt, commence par l'étape 1 et demande à ton humain sur quelle machine il veut tester.
```

---

## Pour Maxime (créateur du kit)

Quand tu reçois le rapport de l'ami :

1. Lis-le en entier sans réagir
2. Trie les retours :
   - **Bloquants** : à fixer avant de redonner au testeur ou de rendre public
   - **Sévères** : à fixer avant le public mais peut attendre quelques jours
   - **Mineurs** : à noter dans un fichier `TODO.md` ou en issues GitHub
3. Réponds au testeur en disant ce que tu prends en compte (= reconnaissance du travail de test)
4. Patche, repush, et redemande un 2ème tour de test si besoin
