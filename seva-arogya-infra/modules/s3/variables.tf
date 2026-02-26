variable "bucket_name" {
  description = "Name of the S3 bucket"
  type        = string
}

variable "enable_versioning" {
  description = "Enable versioning for the bucket"
  type        = bool
  default     = false
}

variable "enable_encryption" {
  description = "Enable server-side encryption"
  type        = bool
  default     = true
}

variable "block_public_access" {
  description = "Block all public access to the bucket"
  type        = bool
  default     = true
}

variable "cors_allowed_origins" {
  description = "List of allowed CORS origins"
  type        = list(string)
  default     = []
}

variable "cors_allowed_methods" {
  description = "List of allowed CORS methods"
  type        = list(string)
  default     = ["GET"]
}

variable "project_name" {
  description = "Project name for resource tagging"
  type        = string
}

variable "env_name" {
  description = "Environment name for resource tagging"
  type        = string
}
