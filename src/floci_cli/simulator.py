"""Fake AWS resource simulator using Moto — provisions S3, DynamoDB, IAM."""
import json
from typing import Any

import boto3
from moto import mock_aws

RESOURCE_TYPES = {
    "aws_s3_bucket": {
        "provider": "aws",
        "aws_service": "s3",
        "terraform_address_template": "aws_s3_bucket.{name}",
    },
    "aws_dynamodb_table": {
        "provider": "aws",
        "aws_service": "dynamodb",
        "terraform_address_template": "aws_dynamodb_table.{name}",
    },
    "aws_iam_role": {
        "provider": "aws",
        "aws_service": "iam",
        "terraform_address_template": "aws_iam_role.{name}",
    },
}

class FakeAwsSimulator:
    """Start Moto mocks, call boto3, produce resource records."""

    def __init__(self, region: str = "us-east-1") -> None:
        self.region = region
        self._mock = mock_aws()
        self._clients: dict[str, Any] = {}

    def start(self) -> None:
        self._mock.start()
        self._clients = {
            "s3": boto3.client("s3", region_name=self.region),
            "dynamodb": boto3.client("dynamodb", region_name=self.region),
            "iam": boto3.client("iam", region_name=self.region),
        }

    def stop(self) -> None:
        self._mock.stop()

    def provision(self, spec: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Create resources from a spec and return their attributes.

        Each spec entry: {"type": "aws_s3_bucket", "name": "my-bucket", ...}
        Returns list of {"type": ..., "attributes": {...}, "address": "..."}
        """
        resources: list[dict[str, Any]] = []
        for item in spec:
            rtype = item["type"]
            if rtype not in RESOURCE_TYPES:
                raise ValueError(
                    f"Unsupported resource type: {rtype}. "
                    f"Supported: {list(RESOURCE_TYPES)}"
                )
            handler = getattr(self, f"_create_{rtype.replace('aws_', '')}", None)
            if handler is None:
                raise ValueError(f"No handler for {rtype}")
            attrs = handler(item)
            info = RESOURCE_TYPES[rtype]
            address = info["terraform_address_template"].format(name=item["name"])
            resources.append({
                "type": rtype,
                "address": address,
                "attributes": attrs,
            })
        return resources

    # -- resource handlers --

    def _create_s3_bucket(self, spec: dict[str, Any]) -> dict[str, Any]:
        bucket_name = spec["name"]
        self._clients["s3"].create_bucket(Bucket=bucket_name)
        return {"bucket": bucket_name, "region": self.region}

    def _create_dynamodb_table(self, spec: dict[str, Any]) -> dict[str, Any]:
        table_name = spec["name"]
        hash_key = spec.get("hash_key", "id")
        billing_mode = spec.get("billing_mode", "PAY_PER_REQUEST")
        self._clients["dynamodb"].create_table(
            TableName=table_name,
            KeySchema=[{"AttributeName": hash_key, "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": hash_key, "AttributeType": "S"}],
            BillingMode=billing_mode,
        )
        return {
            "name": table_name,
            "hash_key": hash_key,
            "billing_mode": billing_mode,
            "region": self.region,
        }

    def _create_iam_role(self, spec: dict[str, Any]) -> dict[str, Any]:
        role_name = spec["name"]
        assume_policy = spec.get("assume_role_policy", json.dumps({
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": {"Service": "ec2.amazonaws.com"},
                "Action": "sts:AssumeRole",
            }],
        }))
        self._clients["iam"].create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=assume_policy,
        )
        return {"name": role_name, "region": self.region}