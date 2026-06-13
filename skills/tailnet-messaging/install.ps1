# tailnet-messaging — Windows installer
#
# Les scripts msg-* sont en Python multiplateforme. Ce script vérifie Python,
# ajoute le dossier scripts/ au PATH utilisateur, et fait des wrappers .cmd
# pour pouvoir lancer "msg-send" depuis n'importe quel terminal.

$ErrorActionPreference = 'Stop'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ScriptsSubDir = Join-Path $ScriptDir 'scripts'

# 1. Vérifier Python
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "⚠ Python n'est pas installé." -ForegroundColor Yellow
    Write-Host "  Installe-le : winget install Python.Python.3.12" -ForegroundColor Cyan
    Write-Host "  Puis relance cet installer."
    exit 1
}

# 2. Créer un dossier d'install dans %LOCALAPPDATA%\Programs
$BinDir = Join-Path $env:LOCALAPPDATA 'Programs\claude-fleet-starter\bin'
New-Item -ItemType Directory -Force -Path $BinDir | Out-Null

# 3. Créer un wrapper .cmd pour chaque script Python
$scripts = @('msg-send', 'msg-receive', 'msg-list', 'msg-show', 'msg-archive', 'msg-list-sessions')
foreach ($s in $scripts) {
    $py = Join-Path $ScriptsSubDir $s
    if (-not (Test-Path $py)) {
        Write-Host "  ⚠ $s introuvable dans $ScriptsSubDir" -ForegroundColor Yellow
        continue
    }
    $cmdFile = Join-Path $BinDir "$s.cmd"
    @"
@echo off
python "$py" %*
"@ | Set-Content -Path $cmdFile -Encoding ASCII
    Write-Host "  ✓ $s.cmd créé dans $BinDir"
}

# 4. Ajouter $BinDir au PATH utilisateur si pas déjà là
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*$BinDir*") {
    $newPath = if ($userPath) { "$userPath;$BinDir" } else { $BinDir }
    [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
    Write-Host "  ✓ $BinDir ajouté au PATH (effectif au prochain démarrage de PowerShell)"
    # Pour la session courante
    $env:Path = "$env:Path;$BinDir"
} else {
    Write-Host "  ✓ $BinDir déjà dans le PATH"
}

Write-Host ""
Write-Host "✓ tailnet-messaging installé." -ForegroundColor Green
Write-Host "  Test : msg-list (devrait afficher 'inbox vide')"
