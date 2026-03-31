param(
  [Parameter(Mandatory = $true)]
  [int]$AppId,

  [Parameter(Mandatory = $true)]
  [string[]]$Files,

  [string]$ApiUrl = "http://sst-core-vm.outergods.lan:4200/api",
  [string]$DeploymentFullName = "sst-worker-pipeline/sst-worker-mvp",
  [switch]$DryRun,
  [switch]$Watch
)

$ErrorActionPreference = "Stop"
$python = "e:/AI_Base/WorkSpace/SST_Project/.venv/Scripts/python.exe"
$env:PREFECT_API_URL = $ApiUrl

$filesJson = ($Files | ConvertTo-Json -Compress)
$dryRunJson = if ($DryRun.IsPresent) { "true" } else { "false" }

$cmd = @(
  "-m", "prefect", "deployment", "run", $DeploymentFullName,
  "--param", "app_id=$AppId",
  "--param", "files=$filesJson",
  "--param", "config_path=worker/config.yaml",
  "--param", "dry_run=$dryRunJson"
)
if ($Watch.IsPresent) {
  $cmd += "--watch"
}

& $python @cmd
if ($LASTEXITCODE -ne 0) {
  throw "Failed to start deployment run: $DeploymentFullName"
}

Write-Host "[OK] Deployment run submitted"
