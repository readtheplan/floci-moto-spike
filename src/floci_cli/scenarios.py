"""Pre-built resource spec scenarios for the CLI."""
from typing import Any

SCENARIOS: dict[str, dict[str, Any]] = {
    "simple": {
        "description": "Single S3 bucket + DynamoDB table + IAM role (3 resources)",
        "resources": [
            {"type": "aws_s3_bucket", "name": "app-logs"},
            {"type": "aws_dynamodb_table", "name": "app-config", "hash_key": "config_key", "billing_mode": "PAY_PER_REQUEST"},
            {"type": "aws_iam_role", "name": "app-service-role"},
        ],
    },
    "full": {
        "description": "Multiple S3 buckets, DynamoDB tables, IAM roles (7 resources)",
        "resources": [
            {"type": "aws_s3_bucket", "name": "static-assets"},
            {"type": "aws_s3_bucket", "name": "cdn-logs"},
            {"type": "aws_s3_bucket", "name": "data-lake"},
            {"type": "aws_dynamodb_table", "name": "sessions", "hash_key": "session_id", "billing_mode": "PAY_PER_REQUEST"},
            {"type": "aws_dynamodb_table", "name": "users", "hash_key": "user_id", "billing_mode": "PAY_PER_REQUEST"},
            {"type": "aws_iam_role", "name": "lambda-exec"},
            {"type": "aws_iam_role", "name": "ecs-task-role"},
        ],
    },
    "mixed": {
        "description": "5 resources of different types: KMS, Lambda, ALB, SG, CloudWatch (5 resources)",
        "resources": [
            {"type": "aws_kms_key", "name": "app-encryption-key", "description": "App encryption key"},
            {"type": "aws_lambda_function", "name": "api-handler", "runtime": "python3.11", "handler": "index.handler"},
            {"type": "aws_lb", "name": "api-alb", "scheme": "internet-facing", "lb_type": "application"},
            {"type": "aws_security_group", "name": "api-sg", "description": "API security group"},
            {"type": "aws_cloudwatch_log_group", "name": "/aws/lambda/api-handler", "retention_in_days": 14},
        ],
    },
    "update": {
        "description": "Scenario that supports update diffs — initial provision + modified state (2 resource versions)",
        "resources": [
            {"type": "aws_s3_bucket", "name": "config-bucket"},
            {"type": "aws_kms_key", "name": "master-key", "description": "Initial description"},
            {"type": "aws_lambda_function", "name": "worker", "runtime": "python3.11", "handler": "index.handler"},
        ],
        "updated_resources": [
            {"type": "aws_s3_bucket", "name": "config-bucket"},
            {"type": "aws_kms_key", "name": "master-key", "description": "Updated description — rotated"},
            {"type": "aws_lambda_function", "name": "worker", "runtime": "python3.12", "handler": "index.handler"},
        ],
    },
    "security": {
        "description": "Security-group-heavy scenario: SGs, IAM roles, KMS keys (6 resources)",
        "resources": [
            {"type": "aws_security_group", "name": "web-sg", "description": "Web tier security group"},
            {"type": "aws_security_group", "name": "app-sg", "description": "Application tier security group"},
            {"type": "aws_security_group", "name": "db-sg", "description": "Database tier security group"},
            {"type": "aws_iam_role", "name": "web-instance-role"},
            {"type": "aws_iam_role", "name": "app-instance-role"},
            {"type": "aws_kms_key", "name": "db-encryption-key", "description": "Database encryption key"},
        ],
    },
}
