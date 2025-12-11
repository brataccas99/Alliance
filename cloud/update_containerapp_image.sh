#!/usr/bin/env bash
set -euo pipefail

# Manual helper to build, push, and deploy the backend image to Azure Container Apps.
# Defaults match the current Terraform outputs; override via env vars if needed.
#
# Env overrides:
#   RG=alliance-pnrr-rg
#   APP=alliance-pnrr-app
#   ACR_NAME=alliancepnrracr.azurecr.io        # login server
#   IMAGE_TAG=alliance-backend:latest
#   REVISION=alliance-pnrr-app--htwlcar        # optional; restart this revision after update

RG="${RG:-alliance-pnrr-rg}"
APP="${APP:-alliance-pnrr-app}"
ACR_NAME="${ACR_NAME:-alliancepnrracr.azurecr.io}"
IMAGE_TAG="${IMAGE_TAG:-alliance-backend:latest}"
REVISION="${REVISION:-}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
CONTEXT="${REPO_ROOT}/Alliance"
DOCKERFILE="${CONTEXT}/backend/Dockerfile"
IMAGE="${ACR_NAME}/${IMAGE_TAG}"

echo "==> Logging into Azure CLI (interactive if not already logged in)"
az login >/dev/null

echo "==> Logging into ACR: ${ACR_NAME}"
az acr login --name "${ACR_NAME%%.azurecr.io}" >/dev/null

echo "==> Building image: ${IMAGE}"
docker build -f "${DOCKERFILE}" -t "${IMAGE}" "${CONTEXT}"

echo "==> Pushing image: ${IMAGE}"
docker push "${IMAGE}"

echo "==> Updating Container App image to ${IMAGE}"
az containerapp update \
  --name "${APP}" \
  --resource-group "${RG}" \
  --image "${IMAGE}" >/dev/null

echo "==> Active revisions (name, active, created, health):"
az containerapp revision list \
  --name "${APP}" \
  --resource-group "${RG}" \
  --query "[].{Name:name, Active:properties.active, Created:properties.createdTime, Health:properties.healthState}"

if [[ -n "${REVISION}" ]]; then
  echo "==> Restarting revision ${REVISION}"
  az containerapp revision restart \
    --name "${APP}" \
    --resource-group "${RG}" \
    --revision "${REVISION}"
fi

echo "==> Tail last 30 log lines"
az containerapp logs show \
  --name "${APP}" \
  --resource-group "${RG}" \
  --tail 30

echo "Done."
