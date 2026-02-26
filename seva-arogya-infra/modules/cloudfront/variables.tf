variable "enabled" {
  description = "Enable CloudFront distribution"
  type        = bool
  default     = true
}

variable "origin_bucket_id" {
  description = "S3 bucket ID for origin"
  type        = string
}

variable "origin_bucket_domain" {
  description = "S3 bucket regional domain name"
  type        = string
}

variable "origin_bucket_arn" {
  description = "S3 bucket ARN"
  type        = string
}

variable "default_root_object" {
  description = "Default root object"
  type        = string
  default     = "index.html"
}

variable "price_class" {
  description = "CloudFront price class"
  type        = string
  default     = "PriceClass_100"
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "env_name" {
  description = "Environment name for resource naming"
  type        = string
}
