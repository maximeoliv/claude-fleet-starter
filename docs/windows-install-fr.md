# Installation sur Windows (sans WSL)

Le kit `claude-fleet-starter` supporte **Windows natif** (sans WSL). Cette page explique :
- Ce qui marche sur Windows
- Ce qui marche de façon dégradée
- Les prérequis
- L'installation pas-à-pas

## Compatible Windows

| Composant | Statut Windows |
|---|---|
| `install.ps1` (wizard PowerShell) | ✓ Natif |
| `tailnet-messaging` | ✓ Natif (Python) |
| `cerveau` | ✓ Natif (Python) |
| `tailscale-secure-form` | ✓ Natif (Python) |
| `claude-state-agent` | ✓ Service Windows (Task Scheduler) |
| `claude-launcher` | ✓ Windows Terminal ou PowerShell window via Task Scheduler |
| `skills-autoupdate` | ✓ Task Scheduler quotidien |
| `claude-on-remote` | ✓ Natif (Python + Tailscale CLI) |
| `onboard-tailnet-machine` | ✓ Natif (Python) |

**Tout est compatible Windows natif**. Pas besoin de WSL.

## Prérequis

Avant de lancer le wizard, installe :

### 1. PowerShell 5.1+ (déjà présent sur Windows 10/11)

Pour vérifier :

```powershell
$PSVersionTable.PSVersion
```

Doit afficher au moins `5.1`. Si moins, mets à jour PowerShell.

### 2. Python 3.10+

Installation via winget (recommandé) :

```powershell
winget install Python.Python.3.12
```

Ou télécharge depuis https://python.org/downloads

⚠ **Important** : à l'installation, coche **"Add python.exe to PATH"**.

### 3. Git (optionnel mais recommandé)

```powershell
winget install --id Git.Git
```

Sans Git, le kit installe via un téléchargement ZIP (pas d'auto-update possible).

### 4. Windows Terminal (recommandé)

```powershell
winget install Microsoft.WindowsTerminal
```

Donne une expérience plus agréable que la console PowerShell standard. Le `claude-launcher` l'utilise si disponible.

## Installation pas-à-pas

### Étape 1 — Ouvre PowerShell en administrateur

Clique-droit sur le menu démarrer → **Windows PowerShell (admin)** ou **Terminal (admin)**.

> 💡 Tu peux faire l'install **en utilisateur normal** (sans admin), mais certaines étapes (notamment ajout au PATH système) peuvent demander l'admin. Le wizard te dira si c'est le cas.

### Étape 2 — Autorise l'exécution de scripts (une seule fois)

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Réponds **O** quand demandé.

### Étape 3 — Lance le wizard

```powershell
iwr https://raw.githubusercontent.com/maximeoliv/claude-fleet-starter/main/install.ps1 -UseBasicParsing | iex
```

Le wizard :
1. Détecte ta version Windows
2. Vérifie les prérequis (Python, etc.)
3. Te demande si tu veux installer Claude Code (si pas déjà là)
4. Te demande si tu veux Tailscale (recommandé pour multi-machine)
5. Te demande si tu veux Remote Control au démarrage (⚠ lis [security.md](remote-control-security.md))
6. Installe les skills
7. Optionnellement bootstrappe depuis ton historique de discussions Claude/ChatGPT

### Étape 4 — Vérifier l'install

Après le wizard, ouvre **un nouveau** PowerShell (pour que les changements de PATH soient pris en compte) et teste :

```powershell
msg-list           # Devrait dire "inbox vide"
cerveau-list       # Devrait afficher les catégories du second cerveau (vides)
claude --version   # Devrait afficher la version de Claude Code
```

## Où vont les fichiers

| Quoi | Où |
|---|---|
| Le kit lui-même | `%USERPROFILE%\.claude-fleet-starter\` |
| Wrappers .cmd des skills | `%LOCALAPPDATA%\Programs\claude-fleet-starter\bin\` |
| Inbox messages | `%USERPROFILE%\inbox\` |
| Second cerveau local | `%USERPROFILE%\cerveau-flotte\` |
| Mémoires Claude Code | `%USERPROFILE%\.claude\projects\...\memory\` |
| Logs auto-update | `%USERPROFILE%\.claude-fleet-starter\autoupdate.log` |

## Tâches planifiées créées

Le wizard crée 2 tâches planifiées (visibles dans Task Scheduler) :

- **`claude-fleet-starter-state-agent`** — lance le claude-state-agent au login
- **`claude-fleet-starter-launcher`** — lance Claude Code dans Windows Terminal/PowerShell au login
- **`claude-fleet-starter-autoupdate`** — pull les skills depuis GitHub tous les jours à 4h

Tu peux les voir avec :

```powershell
Get-ScheduledTask -TaskName "claude-fleet-starter-*"
```

Et les désactiver/supprimer si besoin :

```powershell
Disable-ScheduledTask -TaskName "claude-fleet-starter-autoupdate"
Unregister-ScheduledTask -TaskName "claude-fleet-starter-autoupdate"
```

## Désinstaller

Pas encore d'`uninstall.ps1` propre. À la main :

```powershell
# Arrêter et supprimer les tâches planifiées
Get-ScheduledTask -TaskName "claude-fleet-starter-*" | Unregister-ScheduledTask -Confirm:$false

# Supprimer les wrappers .cmd
Remove-Item -Recurse -Force "$env:LOCALAPPDATA\Programs\claude-fleet-starter"

# Supprimer le kit
Remove-Item -Recurse -Force "$env:USERPROFILE\.claude-fleet-starter"

# Optionnel : supprimer les données utilisateur (mémoires, second cerveau, inbox)
# Remove-Item -Recurse -Force "$env:USERPROFILE\inbox"
# Remove-Item -Recurse -Force "$env:USERPROFILE\cerveau-flotte"

# Nettoyer le PATH (si nécessaire)
# Manuel : Panneau de configuration > Système > Paramètres système avancés > Variables d'environnement
```

## Problèmes courants

### "msg-send n'est pas reconnu"

Cause : le PATH n'a pas été rechargé. Solution : ferme et rouvre PowerShell.

### "Python n'est pas trouvé"

Cause : Python n'a pas été ajouté au PATH à l'installation. Solution : réinstalle Python en cochant **"Add python.exe to PATH"**.

### "Impossible d'enregistrer la tâche planifiée"

Cause : pas de droits administrateur. Solution : relance PowerShell en admin ou skip les services automatiques.

### Le claude-state-agent ne démarre pas

Vérifie les logs dans le Task Scheduler :
- Ouvre **Planificateur de tâches** (taskschd.msc)
- Bibliothèque du Planificateur de tâches → trouve `claude-fleet-starter-state-agent`
- Onglet **Historique** pour voir ce qui a foiré

### Le bootstrap depuis historique échoue

L'analyse d'historique est faite par Claude Code lui-même via le prompt `bootstrap/analyze-history.md`. Si ça échoue, lance Claude Code manuellement et copie-colle le prompt en remplaçant `<CHEMIN>` par le chemin Windows de ton dossier d'historique (avec des `\` ou `/`, les deux marchent).

## Différences avec la version Linux

| Aspect | Linux | Windows |
|---|---|---|
| Langage scripts | Bash | PowerShell |
| Process manager | systemd | Task Scheduler |
| Window manager | tmux | Windows Terminal / PowerShell |
| Symlinks CLI | `/usr/local/bin/` | Wrappers `.cmd` dans `%LOCALAPPDATA%\Programs\...\bin\` |
| Permissions | root souvent requis | Mode user OK la plupart du temps |

Le **fonctionnement utilisateur final est identique** : tu lances les mêmes commandes (`msg-send`, `cerveau-search`, etc.) dans ton terminal, peu importe l'OS.
