# Quick Deploy - Cloud Run (GCP)

Deploy the backend to **Google Cloud Run** (scales to zero, free/low cost for light traffic).

## Deploy

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

## Email notifications

This backend can email subscribers when a fetch discovers new announcements.

1) Configure SMTP and enable notifications in `terraform.tfvars`:

```hcl
email_notifications_enabled = "true"
smtp_host                  = "smtp.example.com"
smtp_port                  = "587"
smtp_username              = "user"
smtp_password              = "pass"
smtp_use_tls               = "true"
email_from                 = "no-reply@example.com"
email_reply_to             = ""
email_subject_prefix       = "[Alliance] "
```

2) Set `MONGO_URI` for persistent subscribers/deduping (otherwise the service falls back to local JSON files, which is not suitable for Cloud Run’s ephemeral filesystem).

## JSON-only persistence (recommended for Cloud Run)

If you want to keep using JSON files (no database), configure a GCS bucket and the app will read/write JSON there:

```hcl
gcs_bucket_name = "your-unique-bucket-name"
gcs_prefix      = "data/"
```

This persists:
- `announcements.json`
- `subscribers.json`
- per-subscriber dedupe files under `notifications/`

## What gets created

1. Cloud Run service (public, autoscaling to zero) using your image
2. Service account for the service
3. Artifact Registry repo (optional image host)
4. IAM to allow unauthenticated access

## `terraform.tfvars` example

```hcl
project_id      = "your-gcp-project-id"
project_name    = "alliance-pnrr"
region          = "europe-west1"
container_image = "gcr.io/your-gcp-project-id/alliance-backend:latest"
debug           = "False"
```

## Updating

- Build & push a new image to the same tag
- `terraform apply` to roll the service

## Cleanup

```bash
cd cloud
terraform destroy
```

This removes the Cloud Run service, repo, and IAM bindings.
