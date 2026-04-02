param(
  [string]$ApiUrl = $(if ($env:PREFECT_API_URL) { $env:PREFECT_API_URL } else { "http://localhost:4200/api" }),
  [string]$PoolName = "sst-worker-pool",
  [string]$QueueName = "sst-default",
  [string]$DeploymentName = "sst-worker-mvp",
  [int]$ConcurrencyLimit = 1
)

$ErrorActionPreference = "Stop"
$python = "e:/AI_Base/WorkSpace/SST_Project/.venv/Scripts/python.exe"

$env:PREFECT_API_URL = $ApiUrl

Push-Location "e:/AI_Base/WorkSpace/SST_Project"
try {
  & $python -m prefect deploy worker/src/pipeline/flow.py:sst_pipeline `
    --no-prompt `
    --name $DeploymentName `
    --pool $PoolName `
    --work-queue $QueueName `
    --concurrency-limit $ConcurrencyLimit `
    --description "SST worker pipeline deployment (AppID + files)"

  if ($LASTEXITCODE -ne 0) {
    throw "Failed to create/update deployment: sst-worker-pipeline/$DeploymentName"
  }
} finally {
  Pop-Location
}

Write-Host "[OK] Deployment is ready: sst-worker-pipeline/$DeploymentName"
