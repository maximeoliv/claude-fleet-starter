# claude-state-agent — Windows installer
#
# Sur Linux : service systemd. Sur Windows : tâche planifiée qui lance le
# serveur uvicorn au démarrage de session utilisateur.
#
# Requiert Python 3.10+ + pip.

$ErrorActionPreference = 'Stop'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "⚠ Python 3.10+ requis (winget install Python.Python.3.12)" -ForegroundColor Yellow
    exit 1
}

# Vérifier la version
$pyVersion = (python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')").Trim()
$pyMajor = [int]($pyVersion.Split('.')[0])
$pyMinor = [int]($pyVersion.Split('.')[1])
if ($pyMajor -lt 3 -or ($pyMajor -eq 3 -and $pyMinor -lt 10)) {
    Write-Host "⚠ Python $pyVersion détecté, il en faut 3.10+." -ForegroundColor Yellow
    exit 1
}

# Créer un venv et installer les dépendances
$VenvDir = Join-Path $ScriptDir '.venv'
if (-not (Test-Path $VenvDir)) {
    Write-Host "→ Création du venv Python..." -ForegroundColor Cyan
    python -m venv $VenvDir
}

$VenvPython = Join-Path $VenvDir 'Scripts\python.exe'
& $VenvPython -m pip install --quiet --upgrade pip
& $VenvPython -m pip install --quiet -e $ScriptDir

# Créer un script de lancement
$LauncherScript = Join-Path $ScriptDir 'run.ps1'
@"
# Lance le claude-state-agent (PowerShell autostart)
Set-Location "$ScriptDir"
& "$VenvPython" -m src.main
"@ | Set-Content -Path $LauncherScript -Encoding UTF8

# Tâche planifiée au démarrage de la session
$TaskName = "claude-fleet-starter-state-agent"
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$LauncherScript`""
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd

try {
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null
    Write-Host "  ✓ Tâche planifiée '$TaskName' enregistrée (démarre à la connexion utilisateur)"
} catch {
    Write-Host "  ⚠ Impossible d'enregistrer la tâche planifiée : $_" -ForegroundColor Yellow
    Write-Host "    Tu peux lancer manuellement : powershell -File $LauncherScript"
}

# Démarrer tout de suite (en background)
try {
    Start-ScheduledTask -TaskName $TaskName
    Write-Host "  ✓ Service démarré"
} catch {
    Write-Host "  ⚠ Démarrage manuel nécessaire (voir logs Task Scheduler)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "✓ claude-state-agent installé." -ForegroundColor Green
Write-Host "  Test : curl http://localhost:18920/health"
