variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "env_name" {
  description = "Environment name for resource naming"
  type        = string
}

variable "s3_pdf_bucket_arn" {
  description = "ARN of the S3 PDF bucket"
  type        = string
}

variable "s3_audio_bucket_arn" {
  description = "ARN of the S3 audio bucket"
  type        = string
}

variable "prescription_pdf_lambda_arn" {
  description = "ARN of prescription PDF Lambda function to invoke from ECS"
  type        = string
  default     = ""
}

variable "enable_prescription_pdf_lambda" {
  description = "Whether prescription PDF Lambda integration is enabled"
  type        = bool
  default     = false
}
