variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "alliance-pnrr"
}

variable "location" {
  description = "Azure region for resources (West Europe is optimal for Italy)"
  type        = string
  default     = "West Europe"
}

variable "debug" {
  description = "Debug mode"
  type        = string
  default     = "False"
}
