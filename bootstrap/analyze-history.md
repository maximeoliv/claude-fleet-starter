# Bootstrap depuis ton historique de discussions IA

## C'est quoi

Si tu as déjà discuté avec Claude (Cowork, Code, claude.ai), ChatGPT, Gemini, Mistral, etc., tu as probablement un dossier d'exports (fichiers `.md`, `.txt`, `.json`, `.jsonl`, `.html`...). Plutôt que de réécrire à la main ton fichier `CLAUDE.md` (= la fiche d'identité de ta machine pour Claude Code), tu peux demander à Claude Code de **lire ton historique** et de **le générer pour toi**.

## Comment utiliser

Une fois Claude Code installé et lancé sur ta machine, copie-colle le prompt suivant dans Claude Code, en remplaçant `<CHEMIN>` par le vrai chemin de ton dossier d'historique.

---

## Prompt à coller dans Claude Code

```
Tu vas analyser mon historique de discussions avec d'autres IA, situé dans <CHEMIN>,
pour générer un fichier CLAUDE.md initial pour cette machine.

## Étapes

1. **Inventaire** : liste les fichiers présents dans le dossier (`ls`, `find -name '*.md' -o -name '*.json' -o -name '*.jsonl' -o -name '*.txt' -o -name '*.html'`). Compte combien il y en a, leur format, et leur ancienneté.

2. **Lecture intelligente** : ne lis PAS tout. Échantillonne :
   - les 5-10 fichiers les plus récents (= contexte le plus à jour)
   - les 5-10 fichiers les plus volumineux (= conversations probablement riches)
   - quelques fichiers anciens (= contexte historique)

3. **Analyse silencieuse** (ne montre pas les détails à l'utilisateur, garde-les pour toi) :
   - Qui est l'utilisateur ? Son nom, son métier, ses projets en cours/passés.
   - Sur quelles machines / quels services travaille-t-il ?
   - Quelles sont ses conventions de travail avec une IA ?
     - Délégation cadrée vs autonome ?
     - Précision technique des questions ?
     - Style de communication (formel/familier, court/long, français/anglais) ?
     - Tolérance à la perte de contexte ?
   - Quels patterns techniques récurrents ? (sécurité, infra, contenu, etc.)
   - Y a-t-il des règles dures explicites ? (« jamais X », « toujours Y »)
   - Y a-t-il des préférences de stack technique exprimées ?

4. **Question à l'utilisateur** (avant de générer) : présente ton diagnostic en 5-10 points (qui tu penses qu'il est, sur quoi il travaille, comment il aime travailler avec une IA), et demande validation/correction. Tu peux te tromper, c'est important qu'il rectifie avant qu'on grave dans le CLAUDE.md.

5. **Génère `/root/CLAUDE.md`** (ou `$HOME/CLAUDE.md` selon le setup) avec une structure type :

   ```markdown
   # CLAUDE.md — <hostname>

   ## Identité
   <hostname, OS, IP locale, role général>

   ## Qui est l'utilisateur ?
   <nom, métier, contexte court — extrait de l'historique>

   ## Projets actifs
   - <projet 1>
   - <projet 2>
   - ...

   ## Conventions de travail avec une IA
   - <observations validées par l'utilisateur>

   ## Règles dures
   <règles explicites trouvées dans l'historique, ou par défaut : pas de secrets en clair,
   pas d'auto-autorisation des outils, doc-as-you-go>

   ## Langue
   <fr / en — détectée depuis l'historique>

   ## Origine
   Généré par bootstrap depuis <CHEMIN>, le <date>.
   ```

6. **Bonus** : si l'historique mentionne des skills/outils déjà utilisés, suggère à l'utilisateur lesquels activer/désactiver dans le kit.

## À éviter

- **Ne lis pas les fichiers contenant des secrets** : si tu vois un fichier nommé `.env`, `secrets.json`, ou si un fichier mentionne des tokens visibles, **saute** et signale à l'utilisateur qu'il devrait vérifier que ces secrets n'ont pas leaké.
- **Ne mets pas de secrets dans `CLAUDE.md`** : noms uniquement, jamais valeurs.
- **Ne fais pas confiance aveuglément à l'historique** : si quelque chose semble obsolète (« je vais essayer X »), considère que c'est juste une exploration passée, pas un fait établi.

## Format de sortie attendu

À la fin de l'opération, affiche :

```
✓ CLAUDE.md généré dans /root/CLAUDE.md (XX lignes)
✓ X mémoires de bonnes pratiques détectées et ajoutées
✓ Y skills suggérés à activer (sur les Z disponibles)

Prochaine étape : lance `cat /root/CLAUDE.md` pour relire,
ou demande-moi d'ajuster un point précis.
```
```

---

## Notes pour les développeurs du kit

Le bootstrap est volontairement un **prompt** plutôt qu'un script. Raisons :

- Le format des historiques varie énormément (JSONL Claude Code, exports Markdown ChatGPT, HTML claude.ai, etc.). Un script devrait coder un parser pour chacun = fragile.
- Claude Code sait lire/échantillonner intelligemment via ses outils Bash/Read/Grep.
- L'utilisateur garde le contrôle (validation manuelle du diagnostic avant écriture).
- C'est plus pédagogique : l'utilisateur voit comment Claude Code travaille, dès le départ.

À évaluer plus tard : un mode "auto" où Claude génère sans demander validation, pour les utilisateurs avancés qui veulent juste un démarrage rapide.
