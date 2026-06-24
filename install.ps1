#Requires -Version 5.1
Add-Type -AssemblyName System.Windows.Forms

$RepoUrl    = "https://github.com/renaudmisslin/intervals-mcp-server-coach.git"
$InstallDir = Join-Path $env:USERPROFILE "intervals-mcp-server-coach"
$ClaudeConfig = Join-Path $env:APPDATA "Claude\claude_desktop_config.json"

function Show-Step($msg) { Write-Host "`n>>> $msg" -ForegroundColor Cyan }
function Show-OK($msg)   { Write-Host "    [OK] $msg" -ForegroundColor Green }
function Show-Err($msg)  { Write-Host "    [ERREUR] $msg" -ForegroundColor Red }
function Has-Cmd($cmd)   { return [bool](Get-Command $cmd -ErrorAction SilentlyContinue) }

function Install-Winget($id, $name) {
    if (-not (Has-Cmd "winget")) { Show-Err "winget non disponible. Installez $name manuellement."; return }
    Write-Host "    Installation de $name..." -ForegroundColor Yellow
    winget install --id $id --silent --accept-source-agreements --accept-package-agreements | Out-Null
    $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH","Machine") + ";" +
                [System.Environment]::GetEnvironmentVariable("PATH","User")
}

Clear-Host
Write-Host "===========================================================" -ForegroundColor Blue
Write-Host "  Installation MCP Coach Intervals.icu - Claude Desktop" -ForegroundColor Blue
Write-Host "===========================================================" -ForegroundColor Blue

# --- Python ---
Show-Step "Verification de Python..."
if (Has-Cmd "python") {
    Show-OK ("Python : " + (python --version 2>&1))
} else {
    Install-Winget "Python.Python.3.12" "Python 3.12"
    if (-not (Has-Cmd "python")) { Show-Err "Python introuvable. Relancez le script."; Read-Host; exit 1 }
    Show-OK "Python installe."
}

# --- Git ---
Show-Step "Verification de Git..."
if (Has-Cmd "git") {
    Show-OK "Git deja installe."
} else {
    Install-Winget "Git.Git" "Git"
    if (-not (Has-Cmd "git")) { Show-Err "Git introuvable. Relancez le script."; Read-Host; exit 1 }
    Show-OK "Git installe."
}

# --- uv ---
Show-Step "Verification de uv..."
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
    if (-not $uvPath) { Show-Err "uv introuvable. Relancez le script."; Read-Host; exit 1 }
}
Show-OK "uv : $uvPath"

# --- Clone ---
Show-Step "Telechargement du projet..."
if (Test-Path (Join-Path $InstallDir ".git")) {
    git -C $InstallDir pull --quiet
    Show-OK "Projet mis a jour : $InstallDir"
} else {
    git clone $RepoUrl $InstallDir --quiet
    Show-OK "Projet clone : $InstallDir"
}

# --- uv sync ---
Show-Step "Installation des dependances Python..."
& $uvPath sync --project $InstallDir --quiet
Show-OK "Dependances installees."

# --- Popup credentials ---
Show-Step "Configuration des identifiants Intervals.icu..."

$form = New-Object System.Windows.Forms.Form
$form.Text = "Configuration MCP Coach Intervals.icu"
$form.Size = New-Object System.Drawing.Size(480, 290)
$form.StartPosition = "CenterScreen"
$form.FormBorderStyle = "FixedDialog"
$form.MaximizeBox = $false

$lbl1 = New-Object System.Windows.Forms.Label
$lbl1.Text = "Cle API coach  (intervals.icu > Settings > API)"
$lbl1.Location = New-Object System.Drawing.Point(20, 20)
$lbl1.Size = New-Object System.Drawing.Size(440, 20)
$form.Controls.Add($lbl1)

$txtKey = New-Object System.Windows.Forms.TextBox
$txtKey.Location = New-Object System.Drawing.Point(20, 45)
$txtKey.Size = New-Object System.Drawing.Size(440, 25)
$form.Controls.Add($txtKey)

$lbl2 = New-Object System.Windows.Forms.Label
$lbl2.Text = "Votre Athlete ID  (meme page, commence par 'i')"
$lbl2.Location = New-Object System.Drawing.Point(20, 90)
$lbl2.Size = New-Object System.Drawing.Size(440, 20)
$form.Controls.Add($lbl2)

$txtId = New-Object System.Windows.Forms.TextBox
$txtId.Location = New-Object System.Drawing.Point(20, 115)
$txtId.Size = New-Object System.Drawing.Size(200, 25)
$form.Controls.Add($txtId)

$lblInfo = New-Object System.Windows.Forms.Label
$lblInfo.Text = "Vos athletes coaches seront detectes automatiquement."
$lblInfo.Location = New-Object System.Drawing.Point(20, 160)
$lblInfo.Size = New-Object System.Drawing.Size(440, 20)
$lblInfo.ForeColor = [System.Drawing.Color]::DarkGray
$form.Controls.Add($lblInfo)

$btn = New-Object System.Windows.Forms.Button
$btn.Text = "Valider"
$btn.Location = New-Object System.Drawing.Point(340, 210)
$btn.Size = New-Object System.Drawing.Size(120, 30)
$btn.DialogResult = [System.Windows.Forms.DialogResult]::OK
$form.AcceptButton = $btn
$form.Controls.Add($btn)

$dlg = $form.ShowDialog()

if ($dlg -ne [System.Windows.Forms.DialogResult]::OK -or
    [string]::IsNullOrWhiteSpace($txtKey.Text) -or
    [string]::IsNullOrWhiteSpace($txtId.Text)) {
    Show-Err "Configuration incomplete. Relancez le script."
    Read-Host; exit 1
}

$apiKey    = $txtKey.Text.Trim()
$athleteId = $txtId.Text.Trim()

# --- .env ---
Show-Step "Ecriture du fichier .env..."
"INTERVALS_ICU_API_KEY=$apiKey`nINTERVALS_ICU_ATHLETE_ID=$athleteId" |
    Set-Content -Path (Join-Path $InstallDir ".env") -Encoding utf8
Show-OK ".env cree."

# --- Claude Desktop config ---
Show-Step "Configuration de Claude Desktop..."
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
Show-OK "Claude Desktop configure."

# --- Claude Desktop present ? ---
Show-Step "Verification de Claude Desktop..."
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
Show-OK "Claude Desktop detecte."

# --- Fin ---
[System.Windows.Forms.MessageBox]::Show(
    "Installation terminee !`n`nRedemarrez Claude Desktop puis tapez :`n`n  Quels athletes est-ce que je coache ?",
    "MCP Coach installe",
    [System.Windows.Forms.MessageBoxButtons]::OK,
    [System.Windows.Forms.MessageBoxIcon]::Information) | Out-Null

Write-Host "`nInstallation terminee. Redemarrez Claude Desktop." -ForegroundColor Green
