# claude-fleet-starter — installer Windows natif (PowerShell)
#
# Ce script:
#   1. Détecte ton OS Windows et ta langue
#   2. Te demande ce que tu veux installer (avec explications adaptées à ton niveau)
#   3. Installe Claude Code (si pas déjà là), Tailscale (si tu veux), et les skills
#   4. Configure les services Windows (via Task Scheduler) selon ton OS
#   5. Te propose de bootstrapper depuis ton historique Claude Cowork / Claude Code si tu en as un
#
# Usage:
#   iwr https://raw.githubusercontent.com/maximeoliv/claude-fleet-starter/main/install.ps1 -UseBasicParsing | iex
#   ou (téléchargé localement) : powershell -ExecutionPolicy Bypass -File install.ps1
#
# License: MIT

$ErrorActionPreference = 'Stop'

# ── 0. Repo and paths ─────────────────────────────────────────────────────────
$Repo = "https://raw.githubusercontent.com/maximeoliv/claude-fleet-starter/main"
$InstallDir = Join-Path $env:USERPROFILE ".claude-fleet-starter"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path -ErrorAction SilentlyContinue
if (-not $ScriptDir) { $ScriptDir = $PWD.Path }

# ── 1. Language detection (i18n) ──────────────────────────────────────────────
$LangCode = (Get-Culture).TwoLetterISOLanguageName
if ($LangCode -ne 'fr' -and $LangCode -ne 'en') { $LangCode = 'en' }
# Allow override via env var
if ($env:CFS_LANG -eq 'fr' -or $env:CFS_LANG -eq 'en') { $LangCode = $env:CFS_LANG }

# ── 2. Source helpers ──────────────────────────────────────────────────────────
# When run via `iwr | iex`, we don't have local lib files — download them.
$LibCache = Join-Path $env:TEMP "cfs-lib"
New-Item -ItemType Directory -Force -Path $LibCache | Out-Null

function Fetch-Lib($name) {
    $dest = Join-Path $LibCache $name
    if (-not (Test-Path $dest)) {
        Invoke-WebRequest -UseBasicParsing "$Repo/lib/$name" -OutFile $dest
    }
    return $dest
}

# Download and source the i18n + helpers
. (Fetch-Lib "i18n/$LangCode.ps1")
. (Fetch-Lib "prompts.ps1")
. (Fetch-Lib "detect-os.ps1")
. (Fetch-Lib "doctor.ps1")

# ── 3. Wizard ─────────────────────────────────────────────────────────────────
Print-Header

# Pre-flight: detect OS
$OsName = Detect-Os
Say $T_OS_DETECTED $OsName

# Pre-flight: check dependencies
Say $T_CHECKING_DEPS
if (-not (Doctor-Check-Basic)) {
    Err $T_DEPS_MISSING
    exit 1
}

# Step 1: Claude Code
$claudeCmd = Get-Command claude -ErrorAction SilentlyContinue
if ($claudeCmd) {
    $ClaudeVersion = (& claude --version 2>&1 | Select-Object -First 1)
    Say $T_CLAUDE_FOUND $ClaudeVersion
} else {
    if (Confirm $T_INSTALL_CLAUDE) {
        Say $T_INSTALLING_CLAUDE
        try {
            Invoke-WebRequest -UseBasicParsing https://claude.ai/install.ps1 | Invoke-Expression
        } catch {
            Warn "L'installer officiel a échoué, fallback npm..."
            $npm = Get-Command npm -ErrorAction SilentlyContinue
            if (-not $npm) {
                Err "npm n'est pas installé. Installe Node.js (winget install OpenJS.NodeJS.LTS) et relance."
                exit 1
            }
            npm install -g "@anthropic-ai/claude-code"
        }
        # Reload PATH in current session
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
        Say $T_CLAUDE_INSTALLED
    } else {
        Say $T_CLAUDE_SKIPPED
    }
}

# Step 2: Tailscale (optional but strongly recommended for multi-machine)
$TailscaleInstalled = $false
$tsCmd = Get-Command tailscale -ErrorAction SilentlyContinue
if ($tsCmd) {
    $TailscaleInstalled = $true
    Say $T_TAILSCALE_FOUND
} else {
    Explain $T_TAILSCALE_WHAT
    if (Confirm $T_INSTALL_TAILSCALE) {
        Say $T_INSTALLING_TAILSCALE
        # Tailscale Windows official installer
        $tsInstaller = Join-Path $env:TEMP "tailscale-setup.exe"
        Invoke-WebRequest -UseBasicParsing "https://pkgs.tailscale.com/stable/tailscale-setup-latest.exe" -OutFile $tsInstaller
        Say "Le programme d'installation Tailscale s'ouvre — suis les étapes graphiques."
        Start-Process -Wait $tsInstaller
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
        $TailscaleInstalled = $true
        Say $T_TAILSCALE_AUTH_NEEDED
        Write-Host ""
        Write-Host "  tailscale up --ssh" -ForegroundColor Bold
        Write-Host ""
        Say $T_PRESS_ENTER_WHEN_DONE
        [void](Read-Host)
    }
}

# Step 3: Remote Control
Explain $T_RC_WHAT
Say $T_RC_SECURITY_WARNING
$EnableRC = (Confirm $T_ENABLE_RC_AUTOSTART)

# Step 4: Skills
Say $T_SKILLS_QUESTION
Explain $T_SKILLS_LIST

# Step 5: Memory starter
$InstallMemory = (Confirm $T_INSTALL_MEMORY_STARTER)

# Step 6: Bootstrap from history
Say $T_BOOTSTRAP_QUESTION
Explain $T_BOOTSTRAP_WHAT
$HistoryPath = ""
if (Confirm $T_BOOTSTRAP_HAS_HISTORY) {
    Say $T_BOOTSTRAP_PATH_PROMPT
    $HistoryPath = Read-Host
    if ($HistoryPath -and -not (Test-Path $HistoryPath)) {
        Warn ($T_BOOTSTRAP_PATH_INVALID -f $HistoryPath)
        $HistoryPath = ""
    }
}

# ── 4. Install ────────────────────────────────────────────────────────────────
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null

# Download skills (cross-platform Python-based ones)
Say "Téléchargement des skills depuis GitHub..."
$SkillsDir = Join-Path $InstallDir "skills"
New-Item -ItemType Directory -Force -Path $SkillsDir | Out-Null

# Use git if available, else download a tarball
$gitCmd = Get-Command git -ErrorAction SilentlyContinue
if ($gitCmd) {
    if (Test-Path "$InstallDir\.git") {
        Push-Location $InstallDir
        git pull --ff-only origin main
        Pop-Location
    } else {
        Push-Location $env:USERPROFILE
        # Clone into a temp dir then move (because $InstallDir already exists)
        $tmpClone = Join-Path $env:TEMP "cfs-clone-$(Get-Random)"
        git clone "https://github.com/maximeoliv/claude-fleet-starter.git" $tmpClone
        Copy-Item -Path "$tmpClone\*" -Destination $InstallDir -Recurse -Force
        Remove-Item -Recurse -Force $tmpClone
        Pop-Location
    }
} else {
    Warn "git n'est pas installé. Installation via ZIP."
    $zipUrl = "https://github.com/maximeoliv/claude-fleet-starter/archive/refs/heads/main.zip"
    $zipFile = Join-Path $env:TEMP "cfs-main.zip"
    Invoke-WebRequest -UseBasicParsing $zipUrl -OutFile $zipFile
    $tmpExtract = Join-Path $env:TEMP "cfs-extract"
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue $tmpExtract
    Expand-Archive -Path $zipFile -DestinationPath $tmpExtract
    Copy-Item -Path "$tmpExtract\claude-fleet-starter-main\*" -Destination $InstallDir -Recurse -Force
    Remove-Item -Recurse -Force $tmpExtract
}

# Install starter memory if requested
if ($InstallMemory) {
    $MemDir = Join-Path $env:USERPROFILE ".claude\projects\$($env:USERPROFILE.Replace('\','-').Replace(':',''))\memory"
    New-Item -ItemType Directory -Force -Path $MemDir | Out-Null
    Copy-Item -Path "$InstallDir\memory-starter\*.md" -Destination $MemDir -Force
    Say $T_MEMORY_INSTALLED
}

# Run each skill's Windows installer (install.ps1) if present, else fall back to install.sh under Git Bash if available
$Skills = @('tailnet-messaging', 'claude-state-agent', 'claude-launcher', 'cerveau', 'tailscale-secure-form', 'skills-autoupdate', 'onboard-tailnet-machine', 'claude-on-remote')
foreach ($skill in $Skills) {
    $skillDir = Join-Path $InstallDir "skills\$skill"
    if (Test-Path $skillDir) {
        Say ($T_INSTALLING_SKILL -f $skill)
        $ps1 = Join-Path $skillDir "install.ps1"
        if (Test-Path $ps1) {
            & powershell -ExecutionPolicy Bypass -File $ps1
        } else {
            Warn "  $skill — pas encore d'installer Windows natif (install.ps1 manquant). Skip pour le moment."
        }
    }
}

# Setup Remote Control autostart via Task Scheduler
if ($EnableRC) {
    Say $T_SETTING_UP_RC_AUTOSTART
    # We rely on claude-launcher's install.ps1 to register a Scheduled Task
    # Placeholder for now
}

# Bootstrap from history if path provided
if ($HistoryPath) {
    Say $T_BOOTSTRAP_RUNNING
    Say ($T_BOOTSTRAP_INSTRUCTIONS -f $HistoryPath)
}

# ── 5. Done ───────────────────────────────────────────────────────────────────
Print-Done-Banner
Say $T_NEXT_STEPS
Write-Host ""
Write-Host "  - claude --remote-control mon-nom-machine"
Write-Host "  - $InstallDir\skills\cerveau\scripts\cerveau-search.ps1 'sujet'"
Write-Host "  - $InstallDir\skills\tailnet-messaging\scripts\msg-send.ps1 --help"
Write-Host ""

if (-not $TailscaleInstalled) {
    Warn $T_TAILSCALE_REMINDER
}

Say $T_DOCS
Write-Host "  https://github.com/maximeoliv/claude-fleet-starter"
