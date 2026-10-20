
variable "aws_region" {
  description = "AWS region for JARVIS development infrastructure."
  type        = string
  default     = "ap-south-1"

  validation {
    condition     = can(regex("^[a-z]{2}(-gov)?-[a-z]+-[0-9]+$", var.aws_region))
    error_message = "Provide a region identifier such as ap-south-1."
  }
}

variable "project_name" {
  description = "Name used to identify JARVIS infrastructure resources."
  type        = string
  default     = "jarvis"
}

variable "environment" {
  description = "Deployment environment."
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}
