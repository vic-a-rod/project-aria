[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$runtimeFile = Join-Path $projectRoot ".aria\runtime.json"

if (-not (Test-Path -LiteralPath $runtimeFile)) {
    Write-Host "No Aria launcher processes are recorded." -ForegroundColor Yellow
    exit 0
}

$runtime = Get-Content -LiteralPath $runtimeFile -Raw | ConvertFrom-Json
foreach ($property in @("frontendPid", "backendPid")) {
    $processId = $runtime.$property
    if ($processId) {
        Stop-Process -Id $processId -ErrorAction SilentlyContinue
    }
}

Remove-Item -LiteralPath $runtimeFile -Force
Write-Host "Aria launcher processes stopped." -ForegroundColor Green

