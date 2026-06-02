"""Fake AWS simulator using Moto."""
from typing import Any

import boto3
from moto import mock_aws

RESOURCE_TYPES = {"aws_s3_bucket", "aws_dynamodb_table", "aws_iam_role"}


class FakeAwsSimulator:
    def __init__(self, region: str = "us-east-1"):
        self.region = region
        self._mock = None
        self._clients: dict[str, Any] = {}

    def start(self):
        self._mock = mock_aws()
        self._mock.start()
        self._clients = {
            "s3": boto3.client("s3", region_name=self.region),
            "dynamodb": boto3.client("dynamodb", region_name=self.region),
            "iam": boto3.client("iam", region_name=self.region),
        }

    def stop(self):
        if self._mock:
            self._mock.stop()
            self._mock = None
            self._clients = {}

    def provision(self, resources: list[dict[str, Any]]) -> list[dict[str, Any]]:
        created = []
        for res in resources:
            rtype = res["type"]
            if rtype not in RESOURCE_TYPES:
                raise ValueError(f"Unsupported resource type: {rtype}")

            if rtype == "aws_s3_bucket":
                bucket = res["name"]
                self._clients["s3"].create_bucket(Bucket=bucket)
                created.append({"type": rtype, "name": bucket, "attributes": {"bucket": bucket}})

            elif rtype == "aws_dynamodb_table":
                table_name = res["name"]
                self._clients["dynamodb"].create_table(
                    TableName=table_name,
                    KeySchema=[{"AttributeName": res.get("hash_key", "id"), "KeyType": "HASH"}],
                    AttributeDefinitions=[{"AttributeName": res.get("hash_key", "id"), "AttributeType": "S"}],
                    BillingMode=res.get("billing_mode", "PAY_PER_REQUEST"),
                )
                created.append({"type": rtype, "name": table_name, "attributes": {"table_name": table_name}})

            elif rtype == "aws_iam_role":
                role_name = res["name"]
                assume_role_policy = res.get("assume_role_policy", {
                    "Version": "2012-10-17",
                    "Statement": [{"Effect": "Allow", "Principal": {"Service": "lambda.amazonaws.com"}, "Action": "sts:AssumeRole"}]
                })
                self._clients["iam"].create_role(RoleName=role_name, AssumeRolePolicyDocument=str(assume_role_policy))
                created.append({"type": rtype, "name": role_name, "attributes": {"role_name": role_name}})

        return created
