param(
  [string]$ApiUrl = $(if ($env:PREFECT_API_URL) { $env:PREFECT_API_URL } else { "http://localhost:4200/api" }),
  [string]$PoolName = "sst-worker-pool",
  [string]$QueueName = "sst-default",
  [string]$WorkerType = "process",
  [int]$QueuePriority = 10
)

$ErrorActionPreference = "Stop"
$python = "e:/AI_Base/WorkSpace/SST_Project/.venv/Scripts/python.exe"

$env:PREFECT_API_URL = $ApiUrl

Write-Host "[INFO] PREFECT_API_URL=$ApiUrl"
Write-Host "[INFO] Ensuring work pool '$PoolName' exists"

& $python -m prefect work-pool inspect $PoolName *> $null
if ($LASTEXITCODE -ne 0) {
  & $python -m prefect work-pool create $PoolName --type $WorkerType
  if ($LASTEXITCODE -ne 0) { throw "Failed to create work pool: $PoolName" }
} else {
  Write-Host "[INFO] Work pool already exists: $PoolName"
}

Write-Host "[INFO] Ensuring work queue '$QueueName' exists in pool '$PoolName'"
$queuesJson = & $python -m prefect work-queue ls --pool $PoolName --output json
if ($LASTEXITCODE -ne 0) { throw "Failed to list work queues for pool: $PoolName" }

$queues = @()
if ($queuesJson) {
  $queues = $queuesJson | ConvertFrom-Json
}

$exists = $false
foreach ($q in $queues) {
  if ($q.name -eq $QueueName) {
    $exists = $true
    break
  }
}

if (-not $exists) {
  & $python -m prefect work-queue create $QueueName --pool $PoolName --priority $QueuePriority
  if ($LASTEXITCODE -ne 0) { throw "Failed to create work queue: $QueueName" }
} else {
  Write-Host "[INFO] Work queue already exists: $QueueName"
}

Write-Host "[OK] Work pool/queue are ready"
