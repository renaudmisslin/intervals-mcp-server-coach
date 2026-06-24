#Requires -Version 5.1
Add-Type -AssemblyName System.Windows.Forms

# ==========================================================
#  MCP Coach Intervals.icu - Script d'installation Windows
#  Base : https://github.com/hhopke/intervals-icu-mcp
#  Modifie par : Renaud Misslin <renaud.misslin@gmail.com>
# ==========================================================

$RepoUrl      = "https://github.com/renaudmisslin/intervals-mcp-server-coach.git"
$InstallDir   = Join-Path $env:USERPROFILE "intervals-mcp-server-coach"
$ClaudeConfig = Join-Path $env:APPDATA "Claude\claude_desktop_config.json"
$TotalSteps   = 7
$Step         = 0

function Next-Step($label) {
    $script:Step++
    Write-Progress -Activity "Installation MCP Coach Intervals.icu" `
                   -Status "Etape $script:Step / $TotalSteps : $label" `
                   -PercentComplete ([int](($script:Step - 1) / $TotalSteps * 100))
    Write-Host "`n>>> [$script:Step/$TotalSteps] $label" -ForegroundColor Cyan
}

function Done-Step($msg) {
    Write-Progress -Activity "Installation MCP Coach Intervals.icu" `
                   -Status "Etape $script:Step / $TotalSteps : OK" `
                   -PercentComplete ([int]($script:Step / $TotalSteps * 100))
    Write-Host "    [OK] $msg" -ForegroundColor Green
}

function Fail-Step($msg) {
    Write-Progress -Activity "Installation MCP Coach Intervals.icu" -Completed
    Write-Host "    [ERREUR] $msg" -ForegroundColor Red
    Read-Host "Appuyez sur Entree pour fermer"
    exit 1
}

function Has-Cmd($cmd) { return [bool](Get-Command $cmd -ErrorAction SilentlyContinue) }

function Install-Winget($id, $name) {
    if (-not (Has-Cmd "winget")) { Fail-Step "winget non disponible. Installez $name manuellement." }
    Write-Host "    Telechargement et installation de $name..." -ForegroundColor Yellow
    winget install --id $id --silent --accept-source-agreements --accept-package-agreements | Out-Null
    $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH","Machine") + ";" +
                [System.Environment]::GetEnvironmentVariable("PATH","User")
}

Clear-Host
Write-Host ""
Write-Host "  MCP Coach Intervals.icu - Installation automatique" -ForegroundColor Blue
Write-Host "  Base sur : https://github.com/hhopke/intervals-icu-mcp" -ForegroundColor DarkGray
Write-Host "  Modifie par : Renaud Misslin <renaud.misslin@gmail.com>" -ForegroundColor DarkGray
Write-Host ""

# --- 1. Python ---
Next-Step "Verification de Python"
if (Has-Cmd "python") {
    Done-Step ("Python deja installe : " + (python --version 2>&1))
} else {
    Install-Winget "Python.Python.3.12" "Python 3.12"
    if (-not (Has-Cmd "python")) { Fail-Step "Python introuvable apres installation. Relancez le script." }
    Done-Step "Python installe."
}

# --- 2. Git ---
Next-Step "Verification de Git"
if (Has-Cmd "git") {
    Done-Step "Git deja installe."
} else {
    Install-Winget "Git.Git" "Git"
    if (-not (Has-Cmd "git")) { Fail-Step "Git introuvable apres installation. Relancez le script." }
    Done-Step "Git installe."
}

# --- 3. uv ---
Next-Step "Verification de uv"
$uvPath = $null
foreach ($p in @("uv", "$env:USERPROFILE\.local\bin\uv.exe", "$env:USERPROFILE\.cargo\bin\uv.exe")) {
    if (Has-Cmd $p) { $uvPath = (Get-Command $p).Source; break }
}
if (-not $uvPath) {
    Write-Host "    Installation de uv..." -ForegroundColor Yellow
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex" | Out-Null
    $env:PATH = $env:PATH + ";$env:USERPROFILE\.local\bin"
    foreach ($p in @("uv", "$env:USERPROFILE\.local\bin\uv.exe")) {
        if (Has-Cmd $p) { $uvPath = (Get-Command $p).Source; break }
    }
    if (-not $uvPath) { Fail-Step "uv introuvable apres installation. Relancez le script." }
}
Done-Step "uv : $uvPath"

# --- 4. Clone / mise a jour ---
Next-Step "Telechargement du projet depuis GitHub"
if (Test-Path (Join-Path $InstallDir ".git")) {
    Write-Host "    Mise a jour du projet existant..." -ForegroundColor Yellow
    git -C $InstallDir pull --quiet
    Done-Step "Projet mis a jour : $InstallDir"
} else {
    Write-Host "    Clonage en cours..." -ForegroundColor Yellow
    git clone $RepoUrl $InstallDir --quiet
    Done-Step "Projet telecharge : $InstallDir"
}

# --- 5. Dependances Python ---
Next-Step "Installation des dependances Python (premiere fois : 1-2 minutes)"
Write-Host "    Installation en cours, merci de patienter..." -ForegroundColor Yellow
& $uvPath sync --project $InstallDir
Done-Step "Dependances installees."

# --- 6. Credentials ---
Next-Step "Configuration des identifiants Intervals.icu"
Write-Host "    Une fenetre pop-up va s'afficher. Completez-la avec votre cle API et votre Athlete ID." -ForegroundColor Yellow
Write-Host "    Ces informations se trouvent sur intervals.icu > Settings > API" -ForegroundColor Yellow

$form = New-Object System.Windows.Forms.Form
$form.Text = "Configuration MCP Coach Intervals.icu"
$form.Size = New-Object System.Drawing.Size(500, 300)
$form.StartPosition = "CenterScreen"
$form.FormBorderStyle = "FixedDialog"
$form.MaximizeBox = $false
$form.TopMost = $true

$lbl1 = New-Object System.Windows.Forms.Label
$lbl1.Text = "Cle API coach  (intervals.icu > Settings > API)"
$lbl1.Location = New-Object System.Drawing.Point(20, 20)
$lbl1.Size = New-Object System.Drawing.Size(460, 20)
$form.Controls.Add($lbl1)

$txtKey = New-Object System.Windows.Forms.TextBox
$txtKey.Location = New-Object System.Drawing.Point(20, 45)
$txtKey.Size = New-Object System.Drawing.Size(460, 25)
$form.Controls.Add($txtKey)

$lbl2 = New-Object System.Windows.Forms.Label
$lbl2.Text = "Votre Athlete ID  (meme page, commence par 'i', ex: i170109)"
$lbl2.Location = New-Object System.Drawing.Point(20, 90)
$lbl2.Size = New-Object System.Drawing.Size(460, 20)
$form.Controls.Add($lbl2)

$txtId = New-Object System.Windows.Forms.TextBox
$txtId.Location = New-Object System.Drawing.Point(20, 115)
$txtId.Size = New-Object System.Drawing.Size(200, 25)
$form.Controls.Add($txtId)

$lblInfo = New-Object System.Windows.Forms.Label
$lblInfo.Text = "Vos athletes coaches seront detectes automatiquement depuis intervals.icu."
$lblInfo.Location = New-Object System.Drawing.Point(20, 160)
$lblInfo.Size = New-Object System.Drawing.Size(460, 20)
$lblInfo.ForeColor = [System.Drawing.Color]::DarkGray
$form.Controls.Add($lblInfo)

$btn = New-Object System.Windows.Forms.Button
$btn.Text = "Valider"
$btn.Location = New-Object System.Drawing.Point(360, 215)
$btn.Size = New-Object System.Drawing.Size(120, 30)
$btn.DialogResult = [System.Windows.Forms.DialogResult]::OK
$form.AcceptButton = $btn
$form.Controls.Add($btn)

$dlg = $form.ShowDialog()

if ($dlg -ne [System.Windows.Forms.DialogResult]::OK -or
    [string]::IsNullOrWhiteSpace($txtKey.Text) -or
    [string]::IsNullOrWhiteSpace($txtId.Text)) {
    Fail-Step "Configuration incomplete. Relancez le script."
}

$apiKey    = $txtKey.Text.Trim()
$athleteId = $txtId.Text.Trim()

"INTERVALS_ICU_API_KEY=$apiKey`nINTERVALS_ICU_ATHLETE_ID=$athleteId" |
    Set-Content -Path (Join-Path $InstallDir ".env") -Encoding utf8
Done-Step ".env cree."

# --- 7. Claude Desktop ---
Next-Step "Configuration de Claude Desktop"

$claudeDir = Split-Path $ClaudeConfig
if (-not (Test-Path $claudeDir)) { New-Item -ItemType Directory -Force $claudeDir | Out-Null }

$mcpBlock = [PSCustomObject]@{
    command = $uvPath
    args    = @("--directory", $InstallDir, "run", "intervals-icu-mcp")
}

if (Test-Path $ClaudeConfig) {
    $cfg = Get-Content $ClaudeConfig -Raw | ConvertFrom-Json
    if (-not $cfg.PSObject.Properties["mcpServers"]) {
        $cfg | Add-Member -MemberType NoteProperty -Name "mcpServers" -Value ([PSCustomObject]@{})
    }
    $cfg.mcpServers | Add-Member -MemberType NoteProperty -Name "intervals-coach" -Value $mcpBlock -Force
    $cfg | ConvertTo-Json -Depth 10 | Set-Content $ClaudeConfig -Encoding utf8
} else {
    [PSCustomObject]@{ mcpServers = [PSCustomObject]@{ "intervals-coach" = $mcpBlock } } |
        ConvertTo-Json -Depth 10 | Set-Content $ClaudeConfig -Encoding utf8
}

$found = Get-ChildItem "$env:LOCALAPPDATA\AnthropicClaude" -Filter "claude.exe" -Recurse -ErrorAction SilentlyContinue |
         Select-Object -First 1
if (-not $found) {
    Write-Host "    Claude Desktop non detecte - ouverture du navigateur..." -ForegroundColor Yellow
    Start-Process "https://claude.ai/download"
    [System.Windows.Forms.MessageBox]::Show(
        "Claude Desktop n'est pas installe.`n`nLa page de telechargement s'est ouverte.`nInstallez-le puis relancez ce script.",
        "Claude Desktop requis",
        [System.Windows.Forms.MessageBoxButtons]::OK,
        [System.Windows.Forms.MessageBoxIcon]::Information) | Out-Null
    exit 0
}
Done-Step "Claude Desktop configure."

Write-Progress -Activity "Installation MCP Coach Intervals.icu" -Completed

[System.Windows.Forms.MessageBox]::Show(
    "Installation terminee !`n`nRedemarrez Claude Desktop puis tapez :`n`n  Quels athletes est-ce que je coache ?",
    "MCP Coach installe",
    [System.Windows.Forms.MessageBoxButtons]::OK,
    [System.Windows.Forms.MessageBoxIcon]::Information) | Out-Null

Write-Host "`nInstallation terminee. Redemarrez Claude Desktop." -ForegroundColor Green
