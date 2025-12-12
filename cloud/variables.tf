variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "alliance-pnrr"
}

variable "region" {
  description = "GCP region for resources (e.g. europe-west1)"
  type        = string
  default     = "europe-west1"
}

variable "container_image" {
  description = "Full container image URL (e.g. gcr.io/your-project/alliance-backend:latest)"
  type        = string
}

variable "debug" {
  description = "Debug mode"
  type        = string
  default     = "False"
}
