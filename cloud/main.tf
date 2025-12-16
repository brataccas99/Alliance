terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Enable required APIs
resource "google_project_service" "run" {
  project = var.project_id
  service = "run.googleapis.com"
}

resource "google_project_service" "artifactregistry" {
  project = var.project_id
  service = "artifactregistry.googleapis.com"
}

resource "google_project_service" "storage" {
  project = var.project_id
  service = "storage.googleapis.com"
}

# Service account for Cloud Run
resource "google_service_account" "run_sa" {
  account_id   = "${var.project_name}-run-sa"
  display_name = "Cloud Run runtime for ${var.project_name}"
}

# Optional: storage bucket for JSON persistence
resource "google_storage_bucket" "json_bucket" {
  count                       = var.gcs_bucket_name != "" ? 1 : 0
  name                        = var.gcs_bucket_name
  location                    = var.region
  uniform_bucket_level_access = true

  depends_on = [google_project_service.storage]
}

resource "google_storage_bucket_iam_member" "json_bucket_admin" {
  count  = var.gcs_bucket_name != "" ? 1 : 0
  bucket = google_storage_bucket.json_bucket[0].name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.run_sa.email}"
}

# Optional: artifact registry to host images (regional)
resource "google_artifact_registry_repository" "repo" {
  location      = var.region
  repository_id = "${var.project_name}-repo"
  description   = "Container images for ${var.project_name}"
  format        = "DOCKER"

  depends_on = [google_project_service.artifactregistry]
}

# Cloud Run service
resource "google_cloud_run_service" "backend" {
  name     = "${var.project_name}-service"
  location = var.region

  template {
    spec {
      service_account_name = google_service_account.run_sa.email

      containers {
        image = var.container_image

        env {
          name  = "FLASK_ENV"
          value = "production"
        }
        env {
          name  = "DEBUG"
          value = var.debug
        }
        env {
          name  = "HOST"
          value = "0.0.0.0"
        }
        env {
          name  = "INITIAL_FETCH"
          value = "false"
        }
        env {
          name  = "SCHEDULER_ENABLED"
          value = "false"
        }
        env {
          name  = "EMAIL_NOTIFICATIONS_ENABLED"
          value = var.email_notifications_enabled
        }
        env {
          name  = "SMTP_HOST"
          value = var.smtp_host
        }
        env {
          name  = "SMTP_PORT"
          value = var.smtp_port
        }
        env {
          name  = "SMTP_USERNAME"
          value = var.smtp_username
        }
        env {
          name  = "SMTP_PASSWORD"
          value = var.smtp_password
        }
        env {
          name  = "SMTP_USE_TLS"
          value = var.smtp_use_tls
        }
        env {
          name  = "EMAIL_FROM"
          value = var.email_from
        }
        env {
          name  = "EMAIL_REPLY_TO"
          value = var.email_reply_to
        }
        env {
          name  = "EMAIL_SUBJECT_PREFIX"
          value = var.email_subject_prefix
        }
        env {
          name  = "APP_BASE_URL"
          value = var.app_base_url
        }
        env {
          name  = "GCS_BUCKET"
          value = var.gcs_bucket_name
        }
        env {
          name  = "GCS_PREFIX"
          value = var.gcs_prefix
        }
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }

  autogenerate_revision_name = true

  depends_on = [google_project_service.run]
}

# Allow unauthenticated access
resource "google_cloud_run_service_iam_member" "public_invoker" {
  location = google_cloud_run_service.backend.location
  project  = var.project_id
  service  = google_cloud_run_service.backend.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
