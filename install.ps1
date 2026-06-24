#Requires -Version 5.1
<#
.SYNOPSIS
    Installation automatique du MCP Coach Intervals.icu pour Claude Desktop.
#>

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName Microsoft.VisualBasic

$RepoUrl  = "https://github.com/renaudmisslin/intervals-mcp-server-coach.git"
$InstallDir = Join-Path $env:USERPROFILE "intervals-mcp-server-coach"
$ClaudeConfig = Join-Path $env:APPDATA "Claude\claude_desktop_config.json"

function Show-Step($msg) {
    Write-Host "`n>>> $msg" -ForegroundColor Cyan
}

function Show-OK($msg) {
    Write-Host "    [OK] $msg" -ForegroundColor Green
}

function Show-Error($msg) {
    Write-Host "    [ERREUR] $msg" -ForegroundColor Red
}

function Test-Command($cmd) {
    return [bool](Get-Command $cmd -ErrorAction SilentlyContinue)
}

function Install-WithWinget($id, $name) {
    if (-not (Test-Command "winget")) {
        Show-Error "winget non disponible. Installez $name manuellement."
        return $false
    }
    Write-Host "    Installation de $name..." -ForegroundColor Yellow
    winget install --id $id --silent --accept-source-agreements --accept-package-agreements | Out-Null
    return $true
}

# ─── Titre ────────────────────────────────────────────────────────────────────
Clear-Host
Write-Host "╔══════════════════════════════════════════════════════════╗" -ForegroundColor Blue
Write-Host "║   Installation MCP Coach Intervals.icu — Claude Desktop  ║" -ForegroundColor Blue
Write-Host "╚══════════════════════════════════════════════════════════╝" -ForegroundColor Blue

# ─── 1. Python ────────────────────────────────────────────────────────────────
Show-Step "Vérification de Python..."
if (Test-Command "python") {
    $v = python --version 2>&1
    Show-OK "Python déjà installé : $v"
} else {
    Install-WithWinget "Python.Python.3.12" "Python 3.12"
    $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH","User")
    if (Test-Command "python") { Show-OK "Python installé." }
    else { Show-Error "Python introuvable après installation. Relancez le script."; Read-Host; exit 1 }
}

# ─── 2. Git ───────────────────────────────────────────────────────────────────
Show-Step "Vérification de Git..."
if (Test-Command "git") {
    Show-OK "Git déjà installé."
} else {
    Install-WithWinget "Git.Git" "Git"
    $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH","User")
    if (Test-Command "git") { Show-OK "Git installé." }
    else { Show-Error "Git introuvable après installation. Relancez le script."; Read-Host; exit 1 }
}

# ─── 3. uv ────────────────────────────────────────────────────────────────────
Show-Step "Vérification de uv..."
$uvPath = $null
foreach ($p in @("uv", "$env:USERPROFILE\.local\bin\uv.exe", "$env:USERPROFILE\.cargo\bin\uv.exe")) {
    if (Test-Command $p) { $uvPath = (Get-Command $p).Source; break }
}
if ($uvPath) {
    Show-OK "uv déjà installé : $uvPath"
} else {
    Write-Host "    Installation de uv..." -ForegroundColor Yellow
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex" | Out-Null
    $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH","User") + ";$env:USERPROFILE\.local\bin"
    foreach ($p in @("uv", "$env:USERPROFILE\.local\bin\uv.exe")) {
        if (Test-Command $p) { $uvPath = (Get-Command $p).Source; break }
    }
    if ($uvPath) { Show-OK "uv installé : $uvPath" }
    else { Show-Error "uv introuvable après installation. Relancez le script."; Read-Host; exit 1 }
}

# ─── 4. Clone / mise à jour du repo ──────────────────────────────────────────
Show-Step "Téléchargement du projet..."
if (Test-Path (Join-Path $InstallDir ".git")) {
    Write-Host "    Mise à jour du projet existant..." -ForegroundColor Yellow
    git -C $InstallDir pull --quiet
    Show-OK "Projet mis à jour dans $InstallDir"
} else {
    git clone $RepoUrl $InstallDir --quiet
    Show-OK "Projet téléchargé dans $InstallDir"
}

# ─── 5. Dépendances Python ────────────────────────────────────────────────────
Show-Step "Installation des dépendances Python..."
& $uvPath sync --project $InstallDir --quiet
Show-OK "Dépendances installées."

# ─── 6. Credentials via popup GUI ────────────────────────────────────────────
Show-Step "Configuration de vos identifiants Intervals.icu..."

$form = New-Object System.Windows.Forms.Form
$form.Text = "Configuration MCP Coach Intervals.icu"
$form.Size = New-Object System.Drawing.Size(480, 280)
$form.StartPosition = "CenterScreen"
$form.FormBorderStyle = "FixedDialog"
$form.MaximizeBox = $false

$lbl1 = New-Object System.Windows.Forms.Label
$lbl1.Text = "Clé API coach (intervals.icu → Settings → API)"
$lbl1.Location = New-Object System.Drawing.Point(20, 20)
$lbl1.Size = New-Object System.Drawing.Size(440, 20)
$form.Controls.Add($lbl1)

$txtKey = New-Object System.Windows.Forms.TextBox
$txtKey.Location = New-Object System.Drawing.Point(20, 45)
$txtKey.Size = New-Object System.Drawing.Size(440, 25)
$txtKey.PlaceholderText = "ex: abc123def456..."
$form.Controls.Add($txtKey)

$lbl2 = New-Object System.Windows.Forms.Label
$lbl2.Text = "Votre Athlete ID (même page, commence par 'i')"
$lbl2.Location = New-Object System.Drawing.Point(20, 90)
$lbl2.Size = New-Object System.Drawing.Size(440, 20)
$form.Controls.Add($lbl2)

$txtId = New-Object System.Windows.Forms.TextBox
$txtId.Location = New-Object System.Drawing.Point(20, 115)
$txtId.Size = New-Object System.Drawing.Size(200, 25)
$txtId.PlaceholderText = "ex: i170109"
$form.Controls.Add($txtId)

$lblHelp = New-Object System.Windows.Forms.Label
$lblHelp.Text = "Vos athlètes coachés seront détectés automatiquement`ndepuis votre compte Intervals.icu."
$lblHelp.Location = New-Object System.Drawing.Point(20, 155)
$lblHelp.Size = New-Object System.Drawing.Size(440, 40)
$lblHelp.ForeColor = [System.Drawing.Color]::DarkGray
$form.Controls.Add($lblHelp)

$btnOK = New-Object System.Windows.Forms.Button
$btnOK.Text = "Valider"
$btnOK.Location = New-Object System.Drawing.Point(340, 205)
$btnOK.Size = New-Object System.Drawing.Size(120, 30)
$btnOK.DialogResult = [System.Windows.Forms.DialogResult]::OK
$form.AcceptButton = $btnOK
$form.Controls.Add($btnOK)

$result = $form.ShowDialog()

if ($result -ne [System.Windows.Forms.DialogResult]::OK -or
    [string]::IsNullOrWhiteSpace($txtKey.Text) -or
    [string]::IsNullOrWhiteSpace($txtId.Text)) {
    Show-Error "Configuration annulée ou incomplète. Relancez le script."
    Read-Host; exit 1
}

$apiKey    = $txtKey.Text.Trim()
$athleteId = $txtId.Text.Trim()

# ─── 7. Écriture du .env ──────────────────────────────────────────────────────
Show-Step "Écriture du fichier .env..."
$envContent = "INTERVALS_ICU_API_KEY=$apiKey`nINTERVALS_ICU_ATHLETE_ID=$athleteId`n"
Set-Content -Path (Join-Path $InstallDir ".env") -Value $envContent -Encoding utf8
Show-OK ".env créé."

# ─── 8. Config Claude Desktop ─────────────────────────────────────────────────
Show-Step "Configuration de Claude Desktop..."

$escapedDir = $InstallDir.Replace("\", "\\")
$mcpEntry = @{
    "intervals-coach" = @{
        command = $uvPath
        args    = @("--directory", $InstallDir, "run", "intervals-icu-mcp")
    }
}

$claudeDir = Split-Path $ClaudeConfig
if (-not (Test-Path $claudeDir)) { New-Item -ItemType Directory -Force $claudeDir | Out-Null }

if (Test-Path $ClaudeConfig) {
    $existing = Get-Content $ClaudeConfig -Raw | ConvertFrom-Json
    if (-not $existing.mcpServers) {
        $existing | Add-Member -MemberType NoteProperty -Name "mcpServers" -Value ([PSCustomObject]@{})
    }
    $existing.mcpServers | Add-Member -MemberType NoteProperty -Name "intervals-coach" -Value $mcpEntry["intervals-coach"] -Force
    $existing | ConvertTo-Json -Depth 10 | Set-Content $ClaudeConfig -Encoding utf8
} else {
    @{ mcpServers = $mcpEntry } | ConvertTo-Json -Depth 10 | Set-Content $ClaudeConfig -Encoding utf8
}
Show-OK "Claude Desktop configuré."

# ─── 9. Claude Desktop installé ? ────────────────────────────────────────────
Show-Step "Vérification de Claude Desktop..."
$claudeExe = Get-ChildItem "$env:LOCALAPPDATA\AnthropicClaude" -Filter "claude.exe" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
if ($claudeExe) {
    Show-OK "Claude Desktop détecté."
} else {
    Write-Host "    Claude Desktop non détecté — ouverture de la page de téléchargement..." -ForegroundColor Yellow
    Start-Process "https://claude.ai/download"
    [System.Windows.Forms.MessageBox]::Show(
        "Claude Desktop n'est pas encore installé.`n`nLa page de téléchargement vient de s'ouvrir dans votre navigateur.`n`nInstallez Claude Desktop, puis relancez ce script pour finaliser.",
        "Claude Desktop requis",
        [System.Windows.Forms.MessageBoxButtons]::OK,
        [System.Windows.Forms.MessageBoxIcon]::Information
    ) | Out-Null
    exit 0
}

# ─── 10. Fin ──────────────────────────────────────────────────────────────────
[System.Windows.Forms.MessageBox]::Show(
    "Installation terminée !`n`nRedémarrez Claude Desktop, puis tapez :`n`n    « Quels athlètes est-ce que je coache ? »",
    "MCP Coach installé",
    [System.Windows.Forms.MessageBoxButtons]::OK,
    [System.Windows.Forms.MessageBoxIcon]::Information
) | Out-Null

Write-Host "`n Installation terminée. Redémarrez Claude Desktop." -ForegroundColor Green
