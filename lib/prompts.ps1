# UI helpers for the interactive PowerShell installer.
# Functions:
#   Print-Header           — colored intro banner
#   Print-Done-Banner      — success banner
#   Say [-fmt] $T_VAR $args  — normal info message (printf-style with -f)
#   Explain $T_VAR         — longer, dimmer explanation
#   Warn / Err             — yellow / red messages
#   Confirm $question      — yes/no prompt (returns bool)

function Print-Header {
    Write-Host $T_HEADER -ForegroundColor Blue
}

function Print-Done-Banner {
    Write-Host $T_DONE_BANNER -ForegroundColor Green
}

function Say {
    param(
        [Parameter(Position = 0)] [string]$Format,
        [Parameter(ValueFromRemainingArguments = $true)] [object[]]$Args
    )
    if ($null -eq $Args -or $Args.Count -eq 0) {
        Write-Host $Format
    } else {
        Write-Host ($Format -f $Args)
    }
}

function Explain {
    param([string]$Format)
    if ($env:CFS_QUIET -eq '1') { return }
    Write-Host $Format -ForegroundColor DarkGray
}

function Warn {
    param([string]$Format)
    Write-Host $Format -ForegroundColor Yellow
}

function Err {
    param([string]$Format)
    Write-Host $Format -ForegroundColor Red
}

function Confirm {
    param([string]$Prompt)
    if ($env:CFS_QUIET -eq '1') { return $true }
    while ($true) {
        Write-Host "$Prompt " -NoNewline -ForegroundColor White
        Write-Host "[O/n] " -NoNewline
        $answer = Read-Host
        switch -Regex ($answer.ToLower()) {
            '^$|^(o|oui|y|yes)$' { return $true }
            '^(n|non|no)$' { return $false }
            default { Write-Host "Réponds par 'o' (oui) ou 'n' (non)." }
        }
    }
}
