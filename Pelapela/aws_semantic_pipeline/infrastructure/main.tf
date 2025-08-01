terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# S3 Bucket for raw data storage
resource "aws_s3_bucket" "raw_data" {
  bucket = "${var.project_name}-raw-data-${random_string.bucket_suffix.result}"
}

resource "aws_s3_bucket_versioning" "raw_data" {
  bucket = aws_s3_bucket.raw_data.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "raw_data" {
  bucket = aws_s3_bucket.raw_data.id

  rule {
    id     = "archive_old_data"
    status = "Enabled"

    transition {
      days          = 90
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 365
      storage_class = "GLACIER"
    }
  }
}

# OpenSearch Serverless Domain
resource "aws_opensearchserverless_collection" "concepts" {
  name = "${var.project_name}-concepts"
  type = "SEARCH"

  description = "Japanese learning concepts with vector embeddings"

  tags = {
    Project = var.project_name
    Purpose = "concept-storage"
  }
}

# IAM Role for Lambda functions
resource "aws_iam_role" "lambda_role" {
  name = "${var.project_name}-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

# IAM Policy for Lambda
resource "aws_iam_role_policy" "lambda_policy" {
  name = "${var.project_name}-lambda-policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = "${aws_s3_bucket.raw_data.arn}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "aoss:*"
        ]
        Resource = aws_opensearchserverless_collection.concepts.arn
      },
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ]
        Resource = "*"
      }
    ]
  })
}

# Lambda function for concept extraction
resource "aws_lambda_function" "concept_extractor" {
  filename         = "../lambda/concept_extractor.zip"
  function_name    = "${var.project_name}-concept-extractor"
  role            = aws_iam_role.lambda_role.arn
  handler         = "concept_extractor.lambda_handler"
  runtime         = "python3.11"
  timeout         = 300
  memory_size     = 1024

  environment {
    variables = {
      OPENSEARCH_ENDPOINT = aws_opensearchserverless_collection.concepts.collection_endpoint
      S3_BUCKET          = aws_s3_bucket.raw_data.bucket
      PROJECT_NAME       = var.project_name
    }
  }

  tags = {
    Project = var.project_name
    Purpose = "concept-extraction"
  }
}

# EventBridge rule to trigger concept extraction
resource "aws_cloudwatch_event_rule" "s3_trigger" {
  name        = "${var.project_name}-s3-trigger"
  description = "Trigger concept extraction when new data is uploaded to S3"

  event_pattern = jsonencode({
    source      = ["aws.s3"]
    detail-type = ["Object Created"]
    detail = {
      bucket = {
        name = [aws_s3_bucket.raw_data.bucket]
      }
    }
  })
}

resource "aws_cloudwatch_event_target" "lambda_target" {
  rule      = aws_cloudwatch_event_rule.s3_trigger.name
  target_id = "ConceptExtractorLambda"
  arn       = aws_lambda_function.concept_extractor.arn
}

resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.concept_extractor.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.s3_trigger.arn
}

# API Gateway for concept queries
resource "aws_api_gateway_rest_api" "concepts_api" {
  name        = "${var.project_name}-concepts-api"
  description = "API for querying Japanese learning concepts"
}

resource "aws_api_gateway_resource" "concepts" {
  rest_api_id = aws_api_gateway_rest_api.concepts_api.id
  parent_id   = aws_api_gateway_rest_api.concepts_api.root_resource_id
  path_part   = "concepts"
}

resource "aws_api_gateway_method" "concepts_get" {
  rest_api_id   = aws_api_gateway_rest_api.concepts_api.id
  resource_id   = aws_api_gateway_resource.concepts.id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_method" "concepts_post" {
  rest_api_id   = aws_api_gateway_rest_api.concepts_api.id
  resource_id   = aws_api_gateway_resource.concepts.id
  http_method   = "POST"
  authorization = "NONE"
}

# Lambda function for API queries
resource "aws_lambda_function" "concept_query" {
  filename         = "../lambda/concept_query.zip"
  function_name    = "${var.project_name}-concept-query"
  role            = aws_iam_role.lambda_role.arn
  handler         = "concept_query.lambda_handler"
  runtime         = "python3.11"
  timeout         = 30
  memory_size     = 512

  environment {
    variables = {
      OPENSEARCH_ENDPOINT = aws_opensearchserverless_collection.concepts.collection_endpoint
      PROJECT_NAME       = var.project_name
    }
  }

  tags = {
    Project = var.project_name
    Purpose = "concept-query"
  }
}

# API Gateway integration
resource "aws_api_gateway_integration" "concepts_get_integration" {
  rest_api_id = aws_api_gateway_rest_api.concepts_api.id
  resource_id = aws_api_gateway_resource.concepts.id
  http_method = aws_api_gateway_method.concepts_get.http_method

  integration_http_method = "POST"
  type                   = "AWS_PROXY"
  uri                    = aws_lambda_function.concept_query.invoke_arn
}

resource "aws_api_gateway_integration" "concepts_post_integration" {
  rest_api_id = aws_api_gateway_rest_api.concepts_api.id
  resource_id = aws_api_gateway_resource.concepts.id
  http_method = aws_api_gateway_method.concepts_post.http_method

  integration_http_method = "POST"
  type                   = "AWS_PROXY"
  uri                    = aws_lambda_function.concept_query.invoke_arn
}

resource "aws_lambda_permission" "allow_api_gateway" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.concept_query.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.concepts_api.execution_arn}/*/*"
}

# API Gateway deployment
resource "aws_api_gateway_deployment" "concepts_api" {
  depends_on = [
    aws_api_gateway_integration.concepts_get_integration,
    aws_api_gateway_integration.concepts_post_integration,
  ]

  rest_api_id = aws_api_gateway_rest_api.concepts_api.id
  stage_name  = "prod"
}

# CloudWatch Log Groups
resource "aws_cloudwatch_log_group" "concept_extractor" {
  name              = "/aws/lambda/${aws_lambda_function.concept_extractor.function_name}"
  retention_in_days = 14
}

resource "aws_cloudwatch_log_group" "concept_query" {
  name              = "/aws/lambda/${aws_lambda_function.concept_query.function_name}"
  retention_in_days = 14
}

# Random string for unique bucket names
resource "random_string" "bucket_suffix" {
  length  = 8
  special = false
  upper   = false
}

# Outputs
output "s3_bucket_name" {
  description = "Name of the S3 bucket for raw data"
  value       = aws_s3_bucket.raw_data.bucket
}

output "opensearch_endpoint" {
  description = "OpenSearch Serverless collection endpoint"
  value       = aws_opensearchserverless_collection.concepts.collection_endpoint
}

output "api_gateway_url" {
  description = "API Gateway URL for concept queries"
  value       = "${aws_api_gateway_deployment.concepts_api.invoke_url}/concepts"
}

output "lambda_functions" {
  description = "Names of the Lambda functions"
  value = {
    concept_extractor = aws_lambda_function.concept_extractor.function_name
    concept_query     = aws_lambda_function.concept_query.function_name
  }
} 