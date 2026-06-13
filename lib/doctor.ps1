# Pre-flight checks for the Windows installer.

function Doctor-Check-Basic {
    $ok = $true

    # PowerShell version
    if ($PSVersionTable.PSVersion.Major -lt 5) {
        Err "PowerShell trop ancien ($($PSVersionTable.PSVersion)). Il te faut au moins 5.1."
        $ok = $false
    }

    # Internet connectivity (try downloading github.com favicon)
    try {
        $null = Invoke-WebRequest -UseBasicParsing -Uri "https://github.com/favicon.ico" -TimeoutSec 5 -ErrorAction Stop
    } catch {
        Err "Pas de connexion Internet (impossible d'atteindre github.com)."
        $ok = $false
    }

    # Optional but useful: git, python3
    $optional = @{
        'git' = "winget install --id Git.Git"
        'python' = "winget install Python.Python.3.12"
    }
    foreach ($cmd in $optional.Keys) {
        if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
            Warn "⚠ $cmd n'est pas installé. Pour Phase 1 ça reste OK, mais certains skills en auront besoin plus tard."
            Warn "   Pour l'installer : $($optional[$cmd])"
        }
    }

    return $ok
}
