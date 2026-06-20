# claude-launcher — Windows installer
#
# Sur Linux : utilise tmux + systemd. Sur Windows : Windows Terminal (si dispo)
# ou nouvelle fenêtre PowerShell, lancée par Task Scheduler à la connexion
# utilisateur.

$ErrorActionPreference = 'Stop'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Détecter Windows Terminal (wt)
$useWindowsTerminal = $false
if (Get-Command wt -ErrorAction SilentlyContinue) {
    $useWindowsTerminal = $true
}

# Le hostname Tailscale (si Tailscale est installé) sert d'identité Remote Control
$rcName = $env:COMPUTERNAME.ToLower()
if (Get-Command tailscale -ErrorAction SilentlyContinue) {
    try {
        $tsSelf = (tailscale status --self --json 2>$null | ConvertFrom-Json).Self
        if ($tsSelf.HostName) { $rcName = $tsSelf.HostName.ToLower() }
    } catch {}
}

# Créer un script de lancement
$LauncherScript = Join-Path $ScriptDir 'launch.ps1'
@"
# Lance Claude Code avec Remote Control au démarrage de session

`$rcName = "$rcName"
`$claudeCmd = "claude -c --remote-control `"`$rcName`" 2>`$null; if (`$LASTEXITCODE -ne 0) { claude --remote-control `"`$rcName`" }"

# Lancer dans Windows Terminal si dispo, sinon nouvelle fenêtre PowerShell
if (Get-Command wt -ErrorAction SilentlyContinue) {
    Start-Process -FilePath "wt" -ArgumentList "new-tab --title `"claude-`$rcName`" powershell -NoExit -Command `"`$claudeCmd`""
} else {
    Start-Process -FilePath "powershell" -ArgumentList "-NoExit", "-Command", `$claudeCmd
}
"@ | Set-Content -Path $LauncherScript -Encoding UTF8

Write-Host "  ✓ scripts/launch.ps1 créé (RC name: $rcName)"

# Tâche planifiée au login
$TaskName = "claude-fleet-starter-launcher"
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$LauncherScript`""
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable

try {
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null
    Write-Host "  ✓ Tâche planifiée '$TaskName' enregistrée"
} catch {
    Write-Host "  ⚠ Impossible d'enregistrer la tâche : $_" -ForegroundColor Yellow
}

# ── claude-fresh wrapper ──────────────────────────────────────────────
# Crée un wrapper .cmd dans %LOCALAPPDATA%\Programs\claude-fleet-starter\bin\
# qui pointe vers scripts/claude-fresh.ps1 (clear les CLAUDE_* env avant
# d'invoquer claude). Permet de relancer claude proprement dans un même
# onglet PowerShell sans héritage de session.
$BinDir = Join-Path $env:LOCALAPPDATA 'Programs\claude-fleet-starter\bin'
New-Item -ItemType Directory -Force -Path $BinDir | Out-Null
$freshScript = Join-Path $ScriptDir 'scripts\claude-fresh.ps1'
if (Test-Path $freshScript) {
    @"
@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$freshScript" %*
"@ | Set-Content -Path (Join-Path $BinDir 'claude-fresh.cmd') -Encoding ASCII
    Write-Host "  ✓ claude-fresh.cmd créé (wrapper pour clear CLAUDE_* env avant claude)"
}

Write-Host ""
Write-Host "✓ claude-launcher installé." -ForegroundColor Green
Write-Host "  Au prochain login, Claude Code se lancera automatiquement dans une nouvelle fenêtre"
Write-Host "  avec Remote Control = '$rcName'."
Write-Host ""
Write-Host "  Tu peux le tester maintenant : powershell -File $LauncherScript"
Write-Host ""
Write-Host "⚠ Bonne pratique Windows" -ForegroundColor Yellow
Write-Host "  Ne relance PAS 'claude' plusieurs fois de suite dans le MÊME onglet PowerShell"
Write-Host "  sans clear les variables d'env de session (CLAUDE_*). Sinon la nouvelle session"
Write-Host "  hérite des artefacts de l'ancienne et le .jsonl de conversation peut ne pas être"
Write-Host "  créé correctement dans %USERPROFILE%\.claude\projects\."
Write-Host ""
Write-Host "  Deux options safes :"
Write-Host "    1. Ouvre un NOUVEL onglet PowerShell à chaque session (le plus simple)"
Write-Host "    2. Utilise la commande 'claude-fresh' qui clear les CLAUDE_* env d'abord"
