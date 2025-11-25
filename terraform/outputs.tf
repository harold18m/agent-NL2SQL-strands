# =============================================================================
# Outputs
# =============================================================================

# -----------------------------------------------------------------------------
# ECR
# -----------------------------------------------------------------------------
output "ecr_repository_url" {
  description = "ECR repository URL"
  value       = aws_ecr_repository.lambda.repository_url
}

output "ecr_repository_arn" {
  description = "ECR repository ARN"
  value       = aws_ecr_repository.lambda.arn
}

# -----------------------------------------------------------------------------
# Lambda
# -----------------------------------------------------------------------------
output "lambda_function_name" {
  description = "Lambda function name"
  value       = aws_lambda_function.api.function_name
}

output "lambda_function_arn" {
  description = "Lambda function ARN"
  value       = aws_lambda_function.api.arn
}

output "lambda_role_arn" {
  description = "Lambda IAM role ARN"
  value       = aws_iam_role.lambda.arn
}

# -----------------------------------------------------------------------------
# Function URL
# -----------------------------------------------------------------------------
output "function_url" {
  description = "Lambda Function URL (HTTP endpoint)"
  value       = aws_lambda_function_url.api.function_url
}

# -----------------------------------------------------------------------------
# GitHub Actions Secrets (sensitive)
# -----------------------------------------------------------------------------
output "github_actions_access_key_id" {
  description = "AWS Access Key ID for GitHub Actions"
  value       = var.create_github_actions_user ? aws_iam_access_key.github_actions[0].id : null
  sensitive   = true
}

output "github_actions_secret_access_key" {
  description = "AWS Secret Access Key for GitHub Actions"
  value       = var.create_github_actions_user ? aws_iam_access_key.github_actions[0].secret : null
  sensitive   = true
}

# -----------------------------------------------------------------------------
# GitHub Actions Configuration
# -----------------------------------------------------------------------------
output "github_secrets_config" {
  description = "Configuration values for GitHub Actions secrets"
  value = {
    AWS_REGION             = data.aws_region.current.name
    ECR_REPOSITORY         = var.ecr_repository_name
    LAMBDA_FUNCTION_NAME   = var.lambda_function_name
  }
}

# -----------------------------------------------------------------------------
# Quick Commands
# -----------------------------------------------------------------------------
output "quick_commands" {
  description = "Useful commands for managing the deployment"
  value = <<-EOT
    
    ============================================
    Quick Commands
    ============================================
    
    # Test the API health endpoint:
    curl ${aws_lambda_function_url.api.function_url}health
    
    # View Lambda logs:
    aws logs tail /aws/lambda/${var.lambda_function_name} --follow
    
    # Update environment variables:
    aws lambda update-function-configuration \
      --function-name ${var.lambda_function_name} \
      --environment 'Variables={DATABASE_URL=your_url,GEMINI_API_KEY=your_key}'
    
    # Get GitHub Actions credentials (run these separately):
    terraform output -raw github_actions_access_key_id
    terraform output -raw github_actions_secret_access_key
    
  EOT
}
