# cerveau — Windows installer
#
# Crée des wrappers .cmd pour les scripts cerveau-*. Le clonage du repo
# cerveau-flotte est laissé à l'utilisateur (configurable via env var
# CERVEAU_REPO ou prompt interactif).

$ErrorActionPreference = 'Stop'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ScriptsSubDir = Join-Path $ScriptDir 'scripts'

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "⚠ Python requis (winget install Python.Python.3.12)" -ForegroundColor Yellow
    exit 1
}

$BinDir = Join-Path $env:LOCALAPPDATA 'Programs\claude-fleet-starter\bin'
New-Item -ItemType Directory -Force -Path $BinDir | Out-Null

$scripts = @('cerveau-search', 'cerveau-recent', 'cerveau-write', 'cerveau-list', 'cerveau-pull')
foreach ($s in $scripts) {
    $py = Join-Path $ScriptsSubDir $s
    if (-not (Test-Path $py)) {
        Write-Host "  ⚠ $s introuvable" -ForegroundColor Yellow
        continue
    }
    $cmdFile = Join-Path $BinDir "$s.cmd"
    @"
@echo off
python "$py" %*
"@ | Set-Content -Path $cmdFile -Encoding ASCII
    Write-Host "  ✓ $s.cmd créé"
}

# Initialiser le dossier ~/cerveau-flotte (vide pour l'instant — l'utilisateur peut le synchroniser avec son repo Git plus tard)
$BrainDir = Join-Path $env:USERPROFILE 'cerveau-flotte'
if (-not (Test-Path $BrainDir)) {
    New-Item -ItemType Directory -Force -Path $BrainDir | Out-Null
    foreach ($cat in @('pulse', 'projects', 'retex', 'patterns', 'audits', 'decisions')) {
        New-Item -ItemType Directory -Force -Path (Join-Path $BrainDir $cat) | Out-Null
    }
    "# Second cerveau — $env:USERNAME`r`n`r`nÀ enrichir au fil du temps." | Set-Content -Path (Join-Path $BrainDir 'README.md') -Encoding UTF8
    Write-Host "  ✓ Dossier $BrainDir créé (vide, prêt à l'emploi)"
} else {
    Write-Host "  ✓ Dossier $BrainDir existe déjà"
}

# PATH
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*$BinDir*") {
    [Environment]::SetEnvironmentVariable("Path", "$userPath;$BinDir", "User")
    $env:Path = "$env:Path;$BinDir"
}

Write-Host ""
Write-Host "✓ cerveau installé." -ForegroundColor Green
Write-Host "  Test : cerveau-list"
Write-Host ""
Write-Host "  💡 Optionnel : pour synchroniser ton cerveau avec un repo Git, fais :"
Write-Host "       cd $BrainDir"
Write-Host "       git init"
Write-Host "       git remote add origin <ton-repo-git>"
Write-Host "       git push -u origin main"
