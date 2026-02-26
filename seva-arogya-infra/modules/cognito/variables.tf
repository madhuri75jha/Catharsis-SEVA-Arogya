variable "user_pool_name" {
  description = "Name of the Cognito User Pool"
  type        = string
}

variable "app_client_name" {
  description = "Name of the Cognito App Client"
  type        = string
}

variable "password_minimum_length" {
  description = "Minimum password length"
  type        = number
  default     = 8
}

variable "password_require_lowercase" {
  description = "Require lowercase characters in password"
  type        = bool
  default     = true
}

variable "password_require_uppercase" {
  description = "Require uppercase characters in password"
  type        = bool
  default     = true
}

variable "password_require_numbers" {
  description = "Require numbers in password"
  type        = bool
  default     = true
}

variable "password_require_symbols" {
  description = "Require symbols in password"
  type        = bool
  default     = true
}

variable "mfa_configuration" {
  description = "MFA configuration (OFF, ON, OPTIONAL)"
  type        = string
  default     = "OFF"
}

variable "email_verification_message" {
  description = "Email verification message"
  type        = string
  default     = "Your verification code is {####}"
}

variable "email_verification_subject" {
  description = "Email verification subject"
  type        = string
  default     = "Your verification code"
}

variable "project_name" {
  description = "Project name for resource tagging"
  type        = string
}

variable "env_name" {
  description = "Environment name for resource tagging"
  type        = string
}
