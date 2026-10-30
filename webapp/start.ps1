$ErrorActionPreference = "Stop"

$projectRoot = Split-Path $PSScriptRoot -Parent
$healthUrl = "http://127.0.0.1:8766/api/health"
$dashboardUrl = "http://127.0.0.1:8766/?sample=us-y1-pod"

$running = $false
try {
    $response = Invoke-RestMethod -Uri $healthUrl -TimeoutSec 2
    $running = $response.status -eq "ok"
} catch {
    $running = $false
}

if (-not $running) {
    Start-Process `
        -FilePath "python" `
        -ArgumentList "webapp/server.py" `
        -WorkingDirectory $projectRoot `
        -WindowStyle Hidden

    for ($attempt = 0; $attempt -lt 20; $attempt++) {
        Start-Sleep -Milliseconds 500
        try {
            $response = Invoke-RestMethod -Uri $healthUrl -TimeoutSec 2
            if ($response.status -eq "ok") {
                $running = $true
                break
            }
        } catch {
            $running = $false
        }
    }
}

if (-not $running) {
    throw "Temu Market Lab failed to start on port 8766."
}

Start-Process $dashboardUrl
