# test-bootstrap.ps1 — version Windows native (PowerShell, pas WSL)
#
# Pour le testeur — ouvre PowerShell, puis tape la commande suivante :
#
#     iwr https://raw.githubusercontent.com/maximeoliv/claude-fleet-starter/main/test-bootstrap.ps1 -UseBasicParsing | iex
#
# Le script installe Claude Code, télécharge le prompt de test, et te dit
# les 2 commandes à taper après pour lancer le test.

$ErrorActionPreference = 'Stop'
$Repo = "https://raw.githubusercontent.com/maximeoliv/claude-fleet-starter/main"

Write-Host ""
Write-Host "╭─────────────────────────────────────────────────────────────╮" -ForegroundColor Blue
Write-Host "│  claude-fleet-starter — bootstrap test (Windows)            │" -ForegroundColor Blue
Write-Host "╰─────────────────────────────────────────────────────────────╯" -ForegroundColor Blue
Write-Host ""

# ── 1. Vérifier la version PowerShell ─────────────────────────────────────────
if ($PSVersionTable.PSVersion.Major -lt 5) {
    Write-Host "⚠ Tu as une vieille version de PowerShell ($($PSVersionTable.PSVersion))." -ForegroundColor Yellow
    Write-Host "  Il te faut au minimum PowerShell 5.1. Sur Windows 10/11 récent c'est par défaut."
    Write-Host "  Si tu es sur Windows 7/8/8.1, mets à jour PowerShell avant de continuer."
    exit 1
}

# ── 2. Détecter Claude Code ───────────────────────────────────────────────────
$claudeCmd = Get-Command claude -ErrorAction SilentlyContinue
if ($claudeCmd) {
    Write-Host "✓ Claude Code est déjà installé." -ForegroundColor Green
    & claude --version 2>&1 | Select-Object -First 1 | Write-Host
} else {
    Write-Host "→ Installation de Claude Code..." -ForegroundColor Cyan

    # Anthropic distribue un installer PowerShell officiel
    # https://claude.ai/install.ps1 (URL à confirmer selon doc Anthropic)
    try {
        Invoke-WebRequest -UseBasicParsing https://claude.ai/install.ps1 | Invoke-Expression
    } catch {
        Write-Host "⚠ L'installer officiel a échoué : $_" -ForegroundColor Yellow
        Write-Host "  On tente via npm en fallback (nécessite Node.js)..."

        $npm = Get-Command npm -ErrorAction SilentlyContinue
        if (-not $npm) {
            Write-Host "⚠ npm n'est pas installé. Installe Node.js d'abord :" -ForegroundColor Yellow
            Write-Host ""
            Write-Host "    winget install OpenJS.NodeJS.LTS" -ForegroundColor Bold
            Write-Host ""
            Write-Host "  Puis relance ce script."
            exit 1
        }
        npm install -g "@anthropic-ai/claude-code"
    }

    # Recharger le PATH dans la session courante
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

    $claudeCmd = Get-Command claude -ErrorAction SilentlyContinue
    if ($claudeCmd) {
        Write-Host "✓ Claude Code installé." -ForegroundColor Green
        & claude --version 2>&1 | Select-Object -First 1 | Write-Host
    } else {
        Write-Host "⚠ L'installation a réussi mais 'claude' n'est pas trouvé dans le PATH." -ForegroundColor Yellow
        Write-Host "  Ferme et rouvre PowerShell, puis relance ce script."
        exit 1
    }
}

# ── 3. Télécharger le prompt de test ──────────────────────────────────────────
$PromptFile = Join-Path $env:TEMP "cfs-test-prompt.txt"
$DocFile = Join-Path $env:TEMP "cfs-test-doc.md"

Write-Host "→ Téléchargement du prompt de test..." -ForegroundColor Cyan
Invoke-WebRequest -UseBasicParsing "$Repo/docs/test-feedback-prompt-fr.md" -OutFile $DocFile

# Extraire juste le bloc de code "Prompt à coller"
$doc = Get-Content $DocFile -Raw -Encoding UTF8
$match = [regex]::Match($doc, '## 📋 Prompt à coller\s*\r?\n\s*```\s*\r?\n(.*?)\r?\n```', [System.Text.RegularExpressions.RegexOptions]::Singleline)
if ($match.Success) {
    $prompt = $match.Groups[1].Value.Trim()
    Set-Content -Path $PromptFile -Value $prompt -Encoding UTF8
    Write-Host "✓ Prompt sauvegardé dans $PromptFile ($($prompt.Length) caractères)" -ForegroundColor Green
} else {
    Write-Host "⚠ Impossible d'extraire le prompt — le fichier source a peut-être changé." -ForegroundColor Yellow
    exit 1
}

# ── 4. Instructions finales ───────────────────────────────────────────────────
Write-Host ""
Write-Host "╭─────────────────────────────────────────────────────────────╮" -ForegroundColor Green
Write-Host "│  ✓ Tout est prêt                                            │" -ForegroundColor Green
Write-Host "╰─────────────────────────────────────────────────────────────╯" -ForegroundColor Green
Write-Host ""
Write-Host "Maintenant 2 commandes à taper toi-même dans PowerShell :" -ForegroundColor Bold
Write-Host ""
Write-Host "  1. Connecte-toi à ton compte Claude :"
Write-Host ""
Write-Host "       claude login" -ForegroundColor Bold
Write-Host ""
Write-Host "     (un lien va s'ouvrir dans ton navigateur, suis-le, valide, reviens ici)"
Write-Host ""
Write-Host "  2. Une fois connecté, lance le test :"
Write-Host ""
Write-Host "       Get-Content $PromptFile | claude" -ForegroundColor Bold
Write-Host ""
Write-Host "     Claude va prendre le prompt en entrée et te guider pour le test."
Write-Host ""
Write-Host "💡 Conseil :" -ForegroundColor Yellow
Write-Host "   Si tu peux, lance ça dans une VM (VirtualBox / Hyper-V / VMware) ou"
Write-Host "   sur une machine de test plutôt que ton ordi principal. Le kit installe"
Write-Host "   pas mal de choses (skills, services, etc.) et c'est encore en alpha."
Write-Host ""
Write-Host "   Note : le kit est conçu pour Linux/Synology — sur Windows pur (sans WSL),"
Write-Host "   tu peux tester la partie 'discussion avec Claude Code' mais l'install"
Write-Host "   des skills va probablement échouer. C'est exactement le genre de retour"
Write-Host "   qu'on cherche."
Write-Host ""
Write-Host "Sois honnête et direct dans tes retours." -ForegroundColor Bold
Write-Host "Maxime préfère un retour qui pique à un retour poli qui ne sert à rien."
Write-Host ""
