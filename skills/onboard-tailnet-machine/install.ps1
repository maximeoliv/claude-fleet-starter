# onboard-tailnet-machine — Windows installer

$ErrorActionPreference = 'Stop'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ScriptsSubDir = Join-Path $ScriptDir 'scripts'

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "⚠ Python requis pour ce skill (winget install Python.Python.3.12)" -ForegroundColor Yellow
    exit 1
}

# Lancer bootstrap-memory.py pour créer une mémoire de démarrage
$bootstrapMem = Join-Path $ScriptsSubDir 'bootstrap-memory.py'
if (Test-Path $bootstrapMem) {
    python $bootstrapMem
} else {
    Write-Host "  ⚠ bootstrap-memory.py introuvable" -ForegroundColor Yellow
}

# Lancer install-permissions-allowlist.py si présent
$permissions = Join-Path $ScriptsSubDir 'install-permissions-allowlist.py'
if (Test-Path $permissions) {
    python $permissions
} else {
    Write-Host "  ⚠ install-permissions-allowlist.py introuvable, skip" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "✓ onboard-tailnet-machine appliqué." -ForegroundColor Green
Write-Host "  Tu peux maintenant éditer/enrichir :"
Write-Host "    %USERPROFILE%\.claude\projects\...\memory\reference_tailnet_basics.md"
