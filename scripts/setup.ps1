$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$backendPath = Join-Path $projectRoot "backend"
$frontendPath = Join-Path $projectRoot "frontend"
$virtualEnvironment = Join-Path $backendPath ".venv"
$pythonPath = Join-Path $virtualEnvironment "Scripts\python.exe"
$envExample = Join-Path $projectRoot ".env.example"
$envFile = Join-Path $projectRoot ".env"

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Python was not found in PATH. Install Python 3.11 or later first."
}

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    throw "npm was not found in PATH. Install Node.js 18 or later first."
}

if (-not (Test-Path -LiteralPath $pythonPath)) {
    python -m venv $virtualEnvironment
}

& $pythonPath -m pip install --upgrade pip
& $pythonPath -m pip install -r (Join-Path $backendPath "requirements.txt")
& $pythonPath (Join-Path $backendPath "manage.py") migrate

Push-Location $frontendPath
try {
    npm install
}
finally {
    Pop-Location
}

if (-not (Test-Path -LiteralPath $envFile)) {
    Copy-Item -LiteralPath $envExample -Destination $envFile
}

Write-Host "Setup complete. Run start_project.bat to launch the application."

