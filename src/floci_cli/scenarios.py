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
}