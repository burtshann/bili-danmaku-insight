$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$backendPath = Join-Path $projectRoot "backend"
$frontendPath = Join-Path $projectRoot "frontend"
$pythonPath = Join-Path $backendPath ".venv\Scripts\python.exe"
$envFile = Join-Path $projectRoot ".env"

if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw "Backend environment is missing. Run scripts/setup.ps1 first."
}

if (-not (Test-Path -LiteralPath (Join-Path $frontendPath "node_modules"))) {
    throw "Frontend dependencies are missing. Run scripts/setup.ps1 first."
}

if (Test-Path -LiteralPath $envFile) {
    foreach ($line in Get-Content -LiteralPath $envFile) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith("#") -or -not $trimmed.Contains("=")) {
            continue
        }

        $parts = $trimmed.Split("=", 2)
        [Environment]::SetEnvironmentVariable($parts[0].Trim(), $parts[1].Trim(), "Process")
    }
}

$npmPath = (Get-Command npm.cmd -ErrorAction Stop).Source

Start-Process `
    -FilePath $pythonPath `
    -ArgumentList @("manage.py", "runserver", "127.0.0.1:8000") `
    -WorkingDirectory $backendPath `
    -WindowStyle Hidden

Start-Process `
    -FilePath $npmPath `
    -ArgumentList @("run", "dev", "--", "--host", "127.0.0.1", "--port", "5173") `
    -WorkingDirectory $frontendPath `
    -WindowStyle Hidden

Start-Sleep -Seconds 3
Start-Process "http://127.0.0.1:5173"

Write-Host "Backend and frontend are starting on ports 8000 and 5173."
