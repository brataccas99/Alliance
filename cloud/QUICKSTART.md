# Quick Deploy - Cloud Run (GCP)

Deploy the backend to **Google Cloud Run** (scales to zero, free/low cost for light traffic).

## 🚀 Deploy

```bash
cd cloud
cp terraform.tfvars.example terraform.tfvars
# edit terraform.tfvars with your project_id, region, and container_image
terraform init
terraform apply
```

Requirements:
- gcloud SDK and Terraform installed
- GCP project with billing enabled
- Container image already built and pushed to Artifact Registry or GCR (set `container_image` in terraform.tfvars)

Terraform auto-enables Cloud Run and Artifact Registry APIs.

## 🌍 What gets created
1. Cloud Run service (public, autoscaling to zero) using your image
2. Service account for the service
3. Artifact Registry repo (optional image host)
4. IAM to allow unauthenticated access

## ⚙️ terraform.tfvars example
```hcl
project_id      = "your-gcp-project-id"
project_name    = "alliance-pnrr"
region          = "europe-west1"
container_image = "gcr.io/your-gcp-project-id/alliance-backend:latest"
debug           = "False"
```

## 🔄 Updating
- Build & push a new image to the same tag
- `terraform apply` to roll the service

## 🧹 Cleanup
```bash
cd cloud
terraform destroy
```

This removes the Cloud Run service, repo, and IAM bindings.
