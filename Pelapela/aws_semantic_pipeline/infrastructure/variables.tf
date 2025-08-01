variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Name of the project (used for resource naming)"
  type        = string
  default     = "pelapela-semantic"
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "lambda_timeout" {
  description = "Timeout for Lambda functions in seconds"
  type        = number
  default     = 300
}

variable "lambda_memory_size" {
  description = "Memory size for Lambda functions in MB"
  type        = number
  default     = 1024
}

variable "opensearch_collection_name" {
  description = "Name for the OpenSearch Serverless collection"
  type        = string
  default     = "japanese-concepts"
}

variable "s3_bucket_name" {
  description = "Name for the S3 bucket (will be made unique)"
  type        = string
  default     = "pelapela-raw-data"
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default = {
    Project     = "Pelapela"
    Purpose     = "Japanese Learning Concepts"
    ManagedBy   = "Terraform"
    Environment = "dev"
  }
} 