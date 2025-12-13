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

# Service account for Cloud Run
resource "google_service_account" "run_sa" {
  account_id   = "${var.project_name}-run-sa"
  display_name = "Cloud Run runtime for ${var.project_name}"
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
