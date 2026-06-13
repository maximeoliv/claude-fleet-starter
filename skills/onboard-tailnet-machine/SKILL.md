# onboard-tailnet-machine — version générique (Phase 1)

Skill qui aide à onboarder une nouvelle machine dans une flotte personnelle de Claude Code.

## Ce qu'il fait

1. **Analyse la machine** (OS, RAM, CPU, disques, services qui tournent, IP, Tailscale)
2. **Génère un `CLAUDE.md` initial** basé sur l'analyse + les conventions standard du kit
3. **Configure la mémoire de démarrage** (règles de sécurité, doc-as-you-go, etc.)
4. **Configure une allowlist de permissions** Claude Code (lecture/écriture des chemins safe, refus des outils destructeurs par défaut)

## Ce qu'il ne fait PAS (à comparer avec la version "flotte" privée)

- Pas de notification Matrix (= demande à l'utilisateur de configurer son propre canal de notif s'il en veut un)
- Pas de configuration SSH Gitea (= l'utilisateur configure son propre Git remote)
- Pas de broadcast automatique à toutes les autres machines de la flotte (= optionnel)

Ces composants peuvent être ajoutés à la main par l'utilisateur après coup.

## Comment utiliser

```bash
bash scripts/detect-machine.sh
python3 scripts/render-claude-md.py --output ~/CLAUDE.md
python3 scripts/install-permissions-allowlist.py
python3 scripts/bootstrap-memory.py
```

Ou via le wizard `install.sh` du kit qui orchestre tout ça.
