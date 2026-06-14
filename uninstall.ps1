# claude-fleet-starter — uninstall script (Windows native).
#
# Removes the Scheduled Tasks we created, the .cmd wrappers in
# %LOCALAPPDATA%\Programs\claude-fleet-starter\bin, and (with confirmation) the
# install dir + user data (inbox, second brain, memory).
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File uninstall.ps1
#   powershell -ExecutionPolicy Bypass -File uninstall.ps1 -KeepData
#   powershell -ExecutionPolicy Bypass -File uninstall.ps1 -Yes
param(
    [switch]$KeepData,
    [switch]$Yes
)

$ErrorActionPreference = 'Stop'
$InstallDir = Join-Path $env:USERPROFILE '.claude-fleet-starter'
$BinDir = Join-Path $env:LOCALAPPDATA 'Programs\claude-fleet-starter'

function Confirm-Action($msg) {
    if ($Yes) { return $true }
    $r = Read-Host "$msg [y/N]"
    return ($r -match '^(y|yes|o|oui)$')
}

Write-Host "claude-fleet-starter uninstall" -ForegroundColor Cyan
Write-Host "Install dir: $InstallDir`n" -ForegroundColor DarkGray

# 1. Scheduled tasks
Write-Host "• Removing scheduled tasks (claude-fleet-starter-*)"
Get-ScheduledTask -TaskName 'claude-fleet-starter-*' -ErrorAction SilentlyContinue |
    ForEach-Object {
        Write-Host "    - $($_.TaskName)"
        try { Unregister-ScheduledTask -TaskName $_.TaskName -Confirm:$false } catch {}
    }

# 2. .cmd wrappers
if (Test-Path $BinDir) {
    Write-Host "• Removing CLI wrappers in $BinDir"
    Remove-Item -Recurse -Force $BinDir
}

# 3. Remove BinDir from User PATH
$userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
if ($userPath -and $userPath -like "*$BinDir*") {
    Write-Host "• Removing $BinDir from User PATH"
    $cleaned = ($userPath -split ';' | Where-Object { $_ -ne $BinDir -and $_ -ne "$BinDir\bin" }) -join ';'
    [Environment]::SetEnvironmentVariable('Path', $cleaned, 'User')
}

# 4. User data (gated)
if ($KeepData) {
    Write-Host "`nData kept: $InstallDir, ~\inbox, ~\cerveau-flotte (use -Yes to remove them too)." -ForegroundColor Yellow
} else {
    Write-Host ""
    if (Confirm-Action "Delete the kit install dir $InstallDir (incl. state-agent token)?") {
        if (Test-Path $InstallDir) { Remove-Item -Recurse -Force $InstallDir; Write-Host "  ✓ removed" }
    }
    $inbox = Join-Path $env:USERPROFILE 'inbox'
    if (Confirm-Action "Delete the inbox at $inbox (received tailnet messages)?") {
        if (Test-Path $inbox) { Remove-Item -Recurse -Force $inbox; Write-Host "  ✓ removed" }
    }
    $brain = Join-Path $env:USERPROFILE 'cerveau-flotte'
    if (Confirm-Action "Delete the second brain at $brain (shared notes — irreversible!)?") {
        if (Test-Path $brain) { Remove-Item -Recurse -Force $brain; Write-Host "  ✓ removed" }
    }
    $memDir = Join-Path $env:USERPROFILE '.claude'
    if (Confirm-Action "Delete Claude Code memory under $memDir?") {
        if (Test-Path $memDir) { Remove-Item -Recurse -Force $memDir; Write-Host "  ✓ removed" }
    }
}

Write-Host "`n✓ Uninstall complete." -ForegroundColor Green
Write-Host "Claude Code and Tailscale were left in place. Uninstall via winget if you want them gone." -ForegroundColor DarkGray
