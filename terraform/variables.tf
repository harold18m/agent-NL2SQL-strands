# =============================================================================
# Variables
# =============================================================================

# -----------------------------------------------------------------------------
# General
# -----------------------------------------------------------------------------
variable "project_name" {
  description = "Name of the project (used for resource naming)"
  type        = string
  default     = "nl2sql-agent"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "us-east-1"
}

# -----------------------------------------------------------------------------
# ECR
# -----------------------------------------------------------------------------
variable "ecr_repository_name" {
  description = "Name of the ECR repository"
  type        = string
  default     = "nl2sql-agent"
}

variable "image_tag" {
  description = "Docker image tag to deploy (use 'latest' for initial deployment)"
  type        = string
  default     = "latest"
}

# -----------------------------------------------------------------------------
# Lambda
# -----------------------------------------------------------------------------
variable "lambda_function_name" {
  description = "Name of the Lambda function"
  type        = string
  default     = "nl2sql-agent"
}

variable "lambda_memory" {
  description = "Memory allocation for Lambda (MB). Recommended: 1024+ for AI agents"
  type        = number
  default     = 1024
}

variable "lambda_timeout" {
  description = "Lambda timeout in seconds. Recommended: 60+ for AI agents"
  type        = number
  default     = 60
}

variable "lambda_environment_variables" {
  description = "Environment variables for Lambda function"
  type        = map(string)
  default     = {}
  sensitive   = true
}

variable "log_level" {
  description = "Log level for the application"
  type        = string
  default     = "INFO"
}

variable "log_retention_days" {
  description = "CloudWatch Logs retention in days"
  type        = number
  default     = 14
}

# -----------------------------------------------------------------------------
# VPC (optional - for RDS access)
# -----------------------------------------------------------------------------
variable "vpc_subnet_ids" {
  description = "List of VPC subnet IDs for Lambda (required for RDS access)"
  type        = list(string)
  default     = null
}

variable "vpc_security_group_ids" {
  description = "List of security group IDs for Lambda"
  type        = list(string)
  default     = null
}

# -----------------------------------------------------------------------------
# Function URL
# -----------------------------------------------------------------------------
variable "function_url_auth_type" {
  description = "Authorization type for Function URL (NONE or AWS_IAM)"
  type        = string
  default     = "NONE"

  validation {
    condition     = contains(["NONE", "AWS_IAM"], var.function_url_auth_type)
    error_message = "function_url_auth_type must be either 'NONE' or 'AWS_IAM'"
  }
}

variable "cors_allowed_origins" {
  description = "Allowed origins for CORS"
  type        = list(string)
  default     = ["*"]
}

# -----------------------------------------------------------------------------
# Secrets Manager (optional)
# -----------------------------------------------------------------------------
variable "enable_secrets_manager" {
  description = "Enable Secrets Manager access for Lambda"
  type        = bool
  default     = false
}

variable "secrets_manager_arns" {
  description = "ARNs of Secrets Manager secrets to allow access"
  type        = list(string)
  default     = []
}

# -----------------------------------------------------------------------------
# GitHub Actions CI/CD
# -----------------------------------------------------------------------------
variable "create_github_actions_user" {
  description = "Create IAM user for GitHub Actions CI/CD"
  type        = bool
  default     = true
}
