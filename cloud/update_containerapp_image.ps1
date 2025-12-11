# Manual helper to build, push, and deploy the backend image to Azure Container Apps.
# Defaults match the current Terraform outputs; override via parameters if needed.
#
# Usage:
#   .\update_containerapp_image.ps1
#   .\update_containerapp_image.ps1 -RG "gro-ai-rg" -APP "gro-ai-app"

param(
    [string]$RG = "alliance-pnrr-rg",
    [string]$APP = "alliance-pnrr-app",
    [string]$ACR_NAME = "alliancepnrracr.azurecr.io",
    [string]$IMAGE_TAG = "alliance-backend:latest",
    [string]$REVISION = ""
)

$ErrorActionPreference = "Stop"

$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$REPO_ROOT = Split-Path -Parent $SCRIPT_DIR
$DOCKERFILE = Join-Path $REPO_ROOT "Alliance\backend\Dockerfile"
$CONTEXT = Join-Path $REPO_ROOT "Alliance"
$IMAGE = "$ACR_NAME/$IMAGE_TAG"

Write-Host "==> Logging into Azure CLI (interactive if not already logged in)" -ForegroundColor Yellow
try {
    $account = az account show --query name -o tsv 2>$null
    if ($LASTEXITCODE -ne 0) {
        az login | Out-Null
    }
} catch {
    az login | Out-Null
}

Write-Host "==> Logging into ACR: $ACR_NAME" -ForegroundColor Yellow
$acrNameShort = $ACR_NAME -replace '\.azurecr\.io$', ''
az acr login --name $acrNameShort | Out-Null

Write-Host "==> Building image: $IMAGE (no cache to ensure fresh build)" -ForegroundColor Yellow
docker build --no-cache -f $DOCKERFILE -t $IMAGE $CONTEXT

Write-Host "==> Pushing image: $IMAGE" -ForegroundColor Yellow
docker push $IMAGE

Write-Host "==> Updating Container App image to $IMAGE" -ForegroundColor Yellow
az containerapp update `
  --name $APP `
  --resource-group $RG `
  --image $IMAGE | Out-Null

Write-Host "==> Getting latest revision name..." -ForegroundColor Yellow
$latestRevision = az containerapp revision list `
  --name $APP `
  --resource-group $RG `
  --query "[0].name" -o tsv

Write-Host "==> Latest revision: $latestRevision" -ForegroundColor Cyan

Write-Host "==> Activating and routing 100% traffic to latest revision..." -ForegroundColor Yellow
az containerapp ingress traffic set `
  --name $APP `
  --resource-group $RG `
  --revision-weight "${latestRevision}=100" | Out-Null

Write-Host "==> Restarting latest revision to ensure new code is loaded..." -ForegroundColor Yellow
az containerapp revision restart `
  --name $APP `
  --resource-group $RG `
  --revision $latestRevision | Out-Null

Write-Host "==> Waiting 10 seconds for restart to complete..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

Write-Host "==> Active revisions (name, active, traffic, created, health):" -ForegroundColor Cyan
az containerapp revision list `
  --name $APP `
  --resource-group $RG `
  --query "[].{Name:name, Active:properties.active, Traffic:properties.trafficWeight, Created:properties.createdTime, Health:properties.healthState}"

Write-Host "==> Deactivating old revisions (keeping only latest)..." -ForegroundColor Yellow
$oldRevisions = az containerapp revision list `
  --name $APP `
  --resource-group $RG `
  --query "[?name != '$latestRevision'].name" -o tsv

foreach ($oldRev in $oldRevisions) {
    if ($oldRev) {
        Write-Host "    Deactivating: $oldRev" -ForegroundColor Gray
        az containerapp revision deactivate `
          --name $APP `
          --resource-group $RG `
          --revision $oldRev 2>$null | Out-Null
    }
}

Write-Host "==> Tail last 30 log lines" -ForegroundColor Cyan
az containerapp logs show `
  --name $APP `
  --resource-group $RG `
  --tail 30

Write-Host ""
Write-Host "==> Verifying deployment..." -ForegroundColor Yellow
$appUrl = az containerapp show `
  --name $APP `
  --resource-group $RG `
  --query "properties.configuration.ingress.fqdn" -o tsv

if ($appUrl) {
    $healthUrl = "https://$appUrl/health"
    Write-Host "    Testing health endpoint: $healthUrl" -ForegroundColor Gray
    try {
        $response = Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec 10
        if ($response.StatusCode -eq 200) {
            Write-Host "    [OK] Health check passed!" -ForegroundColor Green
        } else {
            Write-Host "    [FAILED] Health check returned status: $($response.StatusCode)" -ForegroundColor Red
        }
    } catch {
        Write-Host "    [FAILED] Health check failed: $($_.Exception.Message)" -ForegroundColor Red
    }

    Write-Host ""
    Write-Host "Application URLs:" -ForegroundColor Cyan
    Write-Host "  App: https://$appUrl" -ForegroundColor White
    Write-Host "  Docs: https://$appUrl/docs" -ForegroundColor White
    Write-Host "  Health: https://$appUrl/health" -ForegroundColor White
}

Write-Host ""
Write-Host "Done! Deployment completed successfully." -ForegroundColor Green
