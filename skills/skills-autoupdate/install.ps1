# skills-autoupdate — Windows installer
#
# Sur Linux on utilise un systemd timer. Sur Windows, on utilise le Task
# Scheduler pour lancer un script PowerShell quotidiennement.

$ErrorActionPreference = 'Stop'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Vérifier qu'on a git
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "⚠ git n'est pas installé." -ForegroundColor Yellow
    Write-Host "  Installe-le : winget install --id Git.Git"
    Write-Host "  Puis relance cet installer."
    exit 1
}

$AutoUpdateScript = Join-Path $ScriptDir 'scripts\autoupdate.ps1'
if (-not (Test-Path $AutoUpdateScript)) {
    # Si on n'a pas encore d'autoupdate.ps1, le créer à partir de autoupdate.sh adapté
    $autoupdateContent = @'
# skills-autoupdate — script lancé par Task Scheduler quotidien
# Fait un git pull --ff-only sur chaque skill cloné sous %USERPROFILE%\.claude-fleet-starter\skills\

$LogFile = Join-Path $env:USERPROFILE ".claude-fleet-starter\autoupdate.log"
$SkillsDir = Join-Path $env:USERPROFILE ".claude-fleet-starter\skills"
$Host_ = $env:COMPUTERNAME.ToLower()

"=== $(Get-Date -Format 'yyyy-MM-ddTHH:mm:ss') skills-autoupdate on $Host_ ===" | Add-Content $LogFile

$updates = @()
$failures = @()

if (-not (Test-Path $SkillsDir)) {
    "  no skills dir at $SkillsDir, exiting" | Add-Content $LogFile
    exit 0
}

Get-ChildItem -Path $SkillsDir -Directory | ForEach-Object {
    $skill = $_.Name
    $skillDir = $_.FullName
    if (-not (Test-Path (Join-Path $skillDir ".git"))) { return }

    Push-Location $skillDir
    try {
        $before = (git rev-parse HEAD).Trim()
        git fetch origin --quiet 2>&1 | Out-Null
        $pullResult = git pull --ff-only origin main --quiet 2>&1
        if ($LASTEXITCODE -eq 0) {
            $after = (git rev-parse HEAD).Trim()
            if ($before -ne $after) {
                "  [$skill] $($before.Substring(0,7)) -> $($after.Substring(0,7))" | Add-Content $LogFile
                $updates += "$skill ($($before.Substring(0,7)) → $($after.Substring(0,7)))"
            } else {
                "  [$skill] up to date" | Add-Content $LogFile
            }
        } else {
            "  [$skill] pull FAILED" | Add-Content $LogFile
            $failures += "$skill: pull non-fast-forward"
        }
    } finally {
        Pop-Location
    }
}

# Notification optionnelle via msg-send (env var NOTIFY_HOST)
$notifyHost = $env:NOTIFY_HOST
if (($updates.Count -gt 0 -or $failures.Count -gt 0) -and $notifyHost -and (Get-Command msg-send -ErrorAction SilentlyContinue)) {
    $body = "skills-autoupdate sur $Host_ — $(Get-Date -Format 'yyyy-MM-ddTHH:mm:ss')`r`n`r`n"
    if ($updates.Count -gt 0) {
        $body += "Updates pull --ff-only OK :`r`n"
        foreach ($u in $updates) { $body += "- $u`r`n" }
    }
    if ($failures.Count -gt 0) {
        $body += "`r`nÉchecs :`r`n"
        foreach ($f in $failures) { $body += "- $f`r`n" }
    }
    $tmpFile = Join-Path $env:TEMP "autoupdate-notif.md"
    $body | Set-Content $tmpFile
    msg-send $notifyHost --subject "auto-pull ${Host_}: $($updates.Count) skill(s) updated" --body $tmpFile | Out-Null
    Remove-Item $tmpFile -Force
}

"done" | Add-Content $LogFile
'@
    New-Item -ItemType Directory -Force -Path (Join-Path $ScriptDir 'scripts') | Out-Null
    $autoupdateContent | Set-Content -Path $AutoUpdateScript -Encoding UTF8
    Write-Host "  ✓ scripts/autoupdate.ps1 créé"
}

# Enregistrer une tâche planifiée
$TaskName = "claude-fleet-starter-autoupdate"
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$AutoUpdateScript`""
$trigger = New-ScheduledTaskTrigger -Daily -At "04:00"
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd

try {
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null
    Write-Host "  ✓ Tâche planifiée '$TaskName' enregistrée (lance tous les jours à 4h)"
} catch {
    Write-Host "  ⚠ Impossible d'enregistrer la tâche planifiée : $_" -ForegroundColor Yellow
    Write-Host "    Tu peux lancer manuellement : powershell -File $AutoUpdateScript"
}

Write-Host ""
Write-Host "✓ skills-autoupdate installé." -ForegroundColor Green
Write-Host "  Lance manuellement : powershell -File $AutoUpdateScript"
Write-Host "  Log : %USERPROFILE%\.claude-fleet-starter\autoupdate.log"
