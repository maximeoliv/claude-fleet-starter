# tailscale-secure-form — Windows installer
#
# Crée des wrappers .cmd pour les serveurs Python (intake + display).

$ErrorActionPreference = 'Stop'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ScriptsSubDir = Join-Path $ScriptDir 'scripts'

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "⚠ Python requis (winget install Python.Python.3.12)" -ForegroundColor Yellow
    exit 1
}

$BinDir = Join-Path $env:LOCALAPPDATA 'Programs\claude-fleet-starter\bin'
New-Item -ItemType Directory -Force -Path $BinDir | Out-Null

# Servers : secure_form_server.py (intake user→agent) et secure_display_server.py (display agent→user)
$wrappers = @{
    'secure-form-intake'   = 'secure_form_server.py'
    'secure-form-display'  = 'secure_display_server.py'
}
foreach ($cmd in $wrappers.Keys) {
    $py = Join-Path $ScriptsSubDir $wrappers[$cmd]
    if (-not (Test-Path $py)) {
        Write-Host "  ⚠ $($wrappers[$cmd]) introuvable" -ForegroundColor Yellow
        continue
    }
    $cmdFile = Join-Path $BinDir "$cmd.cmd"
    @"
@echo off
python "$py" %*
"@ | Set-Content -Path $cmdFile -Encoding ASCII
    Write-Host "  ✓ $cmd.cmd créé"
}

$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*$BinDir*") {
    [Environment]::SetEnvironmentVariable("Path", "$userPath;$BinDir", "User")
    $env:Path = "$env:Path;$BinDir"
}

Write-Host ""
Write-Host "✓ tailscale-secure-form installé." -ForegroundColor Green
Write-Host "  Test : secure-form-intake --help"
