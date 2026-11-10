[CmdletBinding()]
param(
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$backendRoot = Join-Path $projectRoot "backend"
$frontendRoot = Join-Path $projectRoot "frontend"
$pythonPath = Join-Path $backendRoot ".venv\Scripts\python.exe"
$vitePath = Join-Path $frontendRoot "node_modules\vite\bin\vite.js"
$runtimeRoot = Join-Path $projectRoot ".aria"
$runtimeFile = Join-Path $runtimeRoot "runtime.json"
$dashboardUrl = "http://localhost:5173"
$apiUrl = "http://127.0.0.1:8000/health"

function Test-AriaEndpoint {
    param([Parameter(Mandatory)][string]$Uri)

    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri $Uri -TimeoutSec 1
        return $response.StatusCode -ge 200 -and $response.StatusCode -lt 500
    }
    catch {
        return $false
    }
}

function Wait-AriaEndpoint {
    param(
        [Parameter(Mandatory)][string]$Uri,
        [Parameter(Mandatory)][string]$Name
    )

    foreach ($attempt in 1..60) {
        if (Test-AriaEndpoint -Uri $Uri) {
            return
        }
        Start-Sleep -Milliseconds 500
    }
    throw "$Name did not become ready. Run 'Stop Aria.cmd', then try again."
}

if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw "Backend setup is missing. Follow README.md once to create backend\.venv."
}
if (-not (Test-Path -LiteralPath $vitePath)) {
    throw "Frontend setup is missing. Run npm install in the frontend folder once."
}
$nodePath = (Get-Command "node.exe" -ErrorAction Stop).Source

New-Item -ItemType Directory -Path $runtimeRoot -Force | Out-Null
$runtime = [ordered]@{}

if (-not (Test-AriaEndpoint -Uri $apiUrl)) {
    $backendProcess = Start-Process `
        -FilePath $pythonPath `
        -ArgumentList @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000") `
        -WorkingDirectory $backendRoot `
        -WindowStyle Hidden `
        -PassThru
    $runtime.backendPid = $backendProcess.Id
}

if (-not (Test-AriaEndpoint -Uri $dashboardUrl)) {
    $frontendProcess = Start-Process `
        -FilePath $nodePath `
        -ArgumentList @($vitePath, "--host", "localhost", "--port", "5173", "--strictPort") `
        -WorkingDirectory $frontendRoot `
        -WindowStyle Hidden `
        -PassThru
    $runtime.frontendPid = $frontendProcess.Id
}

$runtime | ConvertTo-Json | Set-Content -LiteralPath $runtimeFile -Encoding utf8
Wait-AriaEndpoint -Uri $apiUrl -Name "Aria API"
Wait-AriaEndpoint -Uri $dashboardUrl -Name "Aria dashboard"

if (-not $NoBrowser) {
    Start-Process $dashboardUrl
}

Write-Host "Aria is ready at $dashboardUrl" -ForegroundColor Green

