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

variable "email_notifications_enabled" {
  description = "Enable subscriber email notifications"
  type        = string
  default     = "false"
}

variable "smtp_host" {
  description = "SMTP host"
  type        = string
  default     = ""
}

variable "smtp_port" {
  description = "SMTP port"
  type        = string
  default     = "587"
}

variable "smtp_username" {
  description = "SMTP username"
  type        = string
  default     = ""
}

variable "smtp_password" {
  description = "SMTP password"
  type        = string
  default     = ""
  sensitive   = true
}

variable "smtp_use_tls" {
  description = "Use STARTTLS for SMTP"
  type        = string
  default     = "true"
}

variable "email_from" {
  description = "From email address"
  type        = string
  default     = ""
}

variable "email_reply_to" {
  description = "Reply-To email address"
  type        = string
  default     = ""
}

variable "email_subject_prefix" {
  description = "Email subject prefix"
  type        = string
  default     = "[Alliance] "
}

variable "app_base_url" {
  description = "Public base URL (used for unsubscribe links); leave empty to disable links"
  type        = string
  default     = ""
}

variable "gcs_bucket_name" {
  description = "Optional GCS bucket name to persist JSON files (announcements/subscribers/dedupe)"
  type        = string
  default     = ""
}

variable "gcs_prefix" {
  description = "Object prefix within the GCS bucket (e.g. data/)"
  type        = string
  default     = "data/"
}
