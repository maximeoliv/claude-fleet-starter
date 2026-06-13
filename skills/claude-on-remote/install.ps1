# claude-on-remote — Windows installer
#
# Crée des wrappers .cmd pour les scripts Python. Nécessite tailscale CLI
# accessible dans le PATH pour SSH cross-machine.

$ErrorActionPreference = 'Stop'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ScriptsSubDir = Join-Path $ScriptDir 'scripts'

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "⚠ Python requis (winget install Python.Python.3.12)" -ForegroundColor Yellow
    exit 1
}

if (-not (Get-Command tailscale -ErrorAction SilentlyContinue)) {
    Write-Host "⚠ Tailscale CLI requis pour ce skill" -ForegroundColor Yellow
    Write-Host "  Pas bloquant pour l'install, mais le skill ne fera rien sans Tailscale."
}

$BinDir = Join-Path $env:LOCALAPPDATA 'Programs\claude-fleet-starter\bin'
New-Item -ItemType Directory -Force -Path $BinDir | Out-Null

$mainScript = Join-Path $ScriptsSubDir 'claude_on_remote.py'
if (Test-Path $mainScript) {
    @"
@echo off
python "$mainScript" %*
"@ | Set-Content -Path (Join-Path $BinDir 'claude-on-remote.cmd') -Encoding ASCII
    Write-Host "  ✓ claude-on-remote.cmd créé"
}

$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*$BinDir*") {
    [Environment]::SetEnvironmentVariable("Path", "$userPath;$BinDir", "User")
    $env:Path = "$env:Path;$BinDir"
}

Write-Host ""
Write-Host "✓ claude-on-remote installé." -ForegroundColor Green
Write-Host "  Test : claude-on-remote --help"
