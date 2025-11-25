#!/bin/bash
# =============================================================================
# AWS Lambda Setup Script for NL2SQL Agent
# =============================================================================
# This script creates the necessary AWS resources:
# - ECR repository for Docker images
# - IAM role for Lambda execution
# - Lambda function configured for container image
#
# Prerequisites:
# - AWS CLI installed and configured (aws configure)
# - Docker installed
# - Sufficient IAM permissions to create resources
#
# Usage:
#   chmod +x scripts/aws-setup.sh
#   ./scripts/aws-setup.sh
# =============================================================================

set -e

# Configuration - EDIT THESE VALUES
AWS_REGION="${AWS_REGION:-us-east-1}"
ECR_REPO_NAME="${ECR_REPO_NAME:-nl2sql-agent}"
LAMBDA_FUNCTION_NAME="${LAMBDA_FUNCTION_NAME:-nl2sql-agent}"
LAMBDA_MEMORY="${LAMBDA_MEMORY:-1024}"       # MB (recommended for AI agents)
LAMBDA_TIMEOUT="${LAMBDA_TIMEOUT:-60}"       # seconds

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  NL2SQL Agent - AWS Lambda Setup${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Get AWS Account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo -e "${YELLOW}AWS Account:${NC} ${ACCOUNT_ID}"
echo -e "${YELLOW}Region:${NC} ${AWS_REGION}"
echo ""

# -----------------------------------------------------------------------------
# 1. Create ECR Repository
# -----------------------------------------------------------------------------
echo -e "${GREEN}[1/4] Creating ECR repository...${NC}"

if aws ecr describe-repositories --repository-names "${ECR_REPO_NAME}" --region "${AWS_REGION}" > /dev/null 2>&1; then
    echo -e "${YELLOW}  ECR repository '${ECR_REPO_NAME}' already exists, skipping.${NC}"
else
    aws ecr create-repository \
        --repository-name "${ECR_REPO_NAME}" \
        --region "${AWS_REGION}" \
        --image-scanning-configuration scanOnPush=true \
        --encryption-configuration encryptionType=AES256
    echo -e "${GREEN}  ✓ ECR repository created: ${ECR_REPO_NAME}${NC}"
fi

ECR_URI="${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO_NAME}"
echo -e "${YELLOW}  ECR URI: ${ECR_URI}${NC}"
echo ""

# -----------------------------------------------------------------------------
# 2. Create IAM Role for Lambda
# -----------------------------------------------------------------------------
echo -e "${GREEN}[2/4] Creating IAM role for Lambda...${NC}"

ROLE_NAME="${LAMBDA_FUNCTION_NAME}-role"
TRUST_POLICY='{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}'

if aws iam get-role --role-name "${ROLE_NAME}" > /dev/null 2>&1; then
    echo -e "${YELLOW}  IAM role '${ROLE_NAME}' already exists, skipping.${NC}"
else
    aws iam create-role \
        --role-name "${ROLE_NAME}" \
        --assume-role-policy-document "${TRUST_POLICY}" \
        --description "Execution role for ${LAMBDA_FUNCTION_NAME} Lambda"
    
    # Attach basic execution policy (CloudWatch Logs)
    aws iam attach-role-policy \
        --role-name "${ROLE_NAME}" \
        --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
    
    # Attach VPC access policy (if Lambda needs to access RDS in VPC)
    aws iam attach-role-policy \
        --role-name "${ROLE_NAME}" \
        --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole
    
    echo -e "${GREEN}  ✓ IAM role created: ${ROLE_NAME}${NC}"
    
    # Wait for role to propagate
    echo -e "${YELLOW}  Waiting for IAM role to propagate (10s)...${NC}"
    sleep 10
fi

ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}"
echo ""

# -----------------------------------------------------------------------------
# 3. Build and Push Docker Image
# -----------------------------------------------------------------------------
echo -e "${GREEN}[3/4] Building and pushing Docker image...${NC}"

# Login to ECR
aws ecr get-login-password --region "${AWS_REGION}" | docker login --username AWS --password-stdin "${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

# Build image
IMAGE_TAG="latest"
IMAGE_URI="${ECR_URI}:${IMAGE_TAG}"

echo -e "${YELLOW}  Building image: ${IMAGE_URI}${NC}"
docker build -t "${IMAGE_URI}" -f Dockerfile.lambda .

echo -e "${YELLOW}  Pushing image to ECR...${NC}"
docker push "${IMAGE_URI}"

echo -e "${GREEN}  ✓ Image pushed: ${IMAGE_URI}${NC}"
echo ""

# -----------------------------------------------------------------------------
# 4. Create or Update Lambda Function
# -----------------------------------------------------------------------------
echo -e "${GREEN}[4/4] Creating/updating Lambda function...${NC}"

if aws lambda get-function --function-name "${LAMBDA_FUNCTION_NAME}" --region "${AWS_REGION}" > /dev/null 2>&1; then
    echo -e "${YELLOW}  Lambda function exists, updating...${NC}"
    
    aws lambda update-function-code \
        --function-name "${LAMBDA_FUNCTION_NAME}" \
        --image-uri "${IMAGE_URI}" \
        --region "${AWS_REGION}"
    
    # Wait for update to complete
    aws lambda wait function-updated --function-name "${LAMBDA_FUNCTION_NAME}" --region "${AWS_REGION}"
    
    # Update configuration
    aws lambda update-function-configuration \
        --function-name "${LAMBDA_FUNCTION_NAME}" \
        --memory-size "${LAMBDA_MEMORY}" \
        --timeout "${LAMBDA_TIMEOUT}" \
        --region "${AWS_REGION}"
    
    echo -e "${GREEN}  ✓ Lambda function updated${NC}"
else
    echo -e "${YELLOW}  Creating new Lambda function...${NC}"
    
    aws lambda create-function \
        --function-name "${LAMBDA_FUNCTION_NAME}" \
        --package-type Image \
        --code "ImageUri=${IMAGE_URI}" \
        --role "${ROLE_ARN}" \
        --memory-size "${LAMBDA_MEMORY}" \
        --timeout "${LAMBDA_TIMEOUT}" \
        --region "${AWS_REGION}"
    
    # Wait for function to be active
    aws lambda wait function-active --function-name "${LAMBDA_FUNCTION_NAME}" --region "${AWS_REGION}"
    
    echo -e "${GREEN}  ✓ Lambda function created${NC}"
fi

echo ""

# -----------------------------------------------------------------------------
# 5. Create Function URL (optional - for HTTP access without API Gateway)
# -----------------------------------------------------------------------------
echo -e "${GREEN}[5/5] Creating Function URL...${NC}"

FUNCTION_URL=$(aws lambda get-function-url-config --function-name "${LAMBDA_FUNCTION_NAME}" --region "${AWS_REGION}" 2>/dev/null | jq -r '.FunctionUrl' || echo "")

if [ -z "${FUNCTION_URL}" ] || [ "${FUNCTION_URL}" == "null" ]; then
    aws lambda add-permission \
        --function-name "${LAMBDA_FUNCTION_NAME}" \
        --statement-id FunctionURLAllowPublicAccess \
        --action lambda:InvokeFunctionUrl \
        --principal "*" \
        --function-url-auth-type NONE \
        --region "${AWS_REGION}" 2>/dev/null || true
    
    FUNCTION_URL=$(aws lambda create-function-url-config \
        --function-name "${LAMBDA_FUNCTION_NAME}" \
        --auth-type NONE \
        --region "${AWS_REGION}" \
        --query 'FunctionUrl' --output text)
    
    echo -e "${GREEN}  ✓ Function URL created${NC}"
else
    echo -e "${YELLOW}  Function URL already exists${NC}"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}Lambda Function:${NC} ${LAMBDA_FUNCTION_NAME}"
echo -e "${YELLOW}Function URL:${NC} ${FUNCTION_URL}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Configure environment variables:"
echo "   aws lambda update-function-configuration \\"
echo "     --function-name ${LAMBDA_FUNCTION_NAME} \\"
echo "     --environment 'Variables={DATABASE_URL=your_db_url,GEMINI_API_KEY=your_key}'"
echo ""
echo "2. Test the endpoint:"
echo "   curl ${FUNCTION_URL}health"
echo ""
echo "3. Add these secrets to GitHub Actions:"
echo "   - AWS_ACCESS_KEY_ID"
echo "   - AWS_SECRET_ACCESS_KEY"
echo "   - AWS_REGION=${AWS_REGION}"
echo "   - ECR_REPOSITORY=${ECR_REPO_NAME}"
echo "   - LAMBDA_FUNCTION_NAME=${LAMBDA_FUNCTION_NAME}"
echo ""
