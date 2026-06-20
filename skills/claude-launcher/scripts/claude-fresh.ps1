# claude-fresh.ps1 — lance Claude Code en garantissant un environnement propre
#
# Pourquoi ? Sur Windows, si tu retapes `claude` plusieurs fois dans le MÊME
# onglet PowerShell, certaines variables d'env de session (CLAUDE_SESSION_ID,
# CLAUDE_PROJECT_DIR, …) persistent entre les invocations. Conséquence
# observée : la nouvelle session reprend des artefacts de l'ancienne et
# parfois le fichier .jsonl de la nouvelle conversation n'est pas créé
# correctement dans %USERPROFILE%\.claude\projects\<slug>\, ce qui rend la
# session invisible aux outils de découverte (annuaire flotte, etc.).
#
# Ce wrapper évacue les variables d'env Claude avant d'invoquer claude, ce
# qui force la création d'une nouvelle session indépendante dans le même
# onglet PowerShell.
#
# Usage :
#   claude-fresh [args...]
# Tous les arguments sont passés tels quels au binaire claude.
#
# Si tu préfères, la même protection est obtenue en ouvrant simplement un
# NOUVEL onglet PowerShell à chaque session Claude Code (plus simple, plus
# safe). Ce wrapper est utile quand tu veux quand même réutiliser le même
# onglet.

# Nettoie toutes les variables d'env qui commencent par CLAUDE_
$cleared = @()
foreach ($v in (Get-ChildItem env:CLAUDE_* -ErrorAction SilentlyContinue)) {
    Remove-Item "env:$($v.Name)" -ErrorAction SilentlyContinue
    $cleared += $v.Name
}

if ($cleared.Count -gt 0) {
    Write-Host "claude-fresh: cleared $($cleared.Count) CLAUDE_* env var(s): $($cleared -join ', ')" -ForegroundColor DarkGray
}

# Lance claude avec les arguments passés
$claudeBin = Get-Command claude -ErrorAction SilentlyContinue
if (-not $claudeBin) {
    Write-Host "claude binary not found in PATH" -ForegroundColor Red
    exit 1
}

& $claudeBin.Source @args
exit $LASTEXITCODE
