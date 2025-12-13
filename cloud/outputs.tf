output "service_url" {
  description = "Public URL of the Cloud Run service"
  value       = google_cloud_run_service.backend.status[0].url
}

output "run_service_name" {
  description = "Deployed Cloud Run service name"
  value       = google_cloud_run_service.backend.name
}

output "artifact_registry_repo" {
  description = "Artifact Registry repo URL (if used)"
  value       = "${google_artifact_registry_repository.repo.location}-docker.pkg.dev/${google_artifact_registry_repository.repo.project}/${google_artifact_registry_repository.repo.repository_id}"
}

output "service_account_email" {
  description = "Service account used by Cloud Run"
  value       = google_service_account.run_sa.email
}
