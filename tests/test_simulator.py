"""Tests for floci_cli.simulator — the Moto-based fake AWS engine."""
import pytest
from floci_cli.simulator import FakeAwsSimulator, RESOURCE_TYPES

def test_simulator_creates_s3_bucket():
    sim = FakeAwsSimulator(region="us-east-1")
    sim.start()
    resources = sim.provision([
        {"type": "aws_s3_bucket", "name": "my-logs-bucket"},
    ])
    sim.stop()

    assert len(resources) == 1
    assert resources[0]["type"] == "aws_s3_bucket"
    assert resources[0]["attributes"]["bucket"] == "my-logs-bucket"

def test_simulator_creates_dynamodb_table():
    sim = FakeAwsSimulator(region="us-east-1")
    sim.start()
    resources = sim.provision([
        {
            "type": "aws_dynamodb_table",
            "name": "users-table",
            "hash_key": "id",
            "billing_mode": "PAY_PER_REQUEST",
        },
    ])
    sim.stop()

    assert len(resources) == 1
    assert resources[0]["type"] == "aws_dynamodb_table"
    attrs = resources[0]["attributes"]
    assert attrs["name"] == "users-table"
    assert attrs["hash_key"] == "id"
    assert attrs["billing_mode"] == "PAY_PER_REQUEST"

def test_simulator_creates_iam_role():
    sim = FakeAwsSimulator(region="us-east-1")
    sim.start()
    resources = sim.provision([
        {
            "type": "aws_iam_role",
            "name": "lambda-exec-role",
            "assume_role_policy": '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"lambda.amazonaws.com"},"Action":"sts:AssumeRole"}]}',
        },
    ])
    sim.stop()

    assert len(resources) == 1
    assert resources[0]["type"] == "aws_iam_role"
    assert resources[0]["attributes"]["name"] == "lambda-exec-role"

def test_simulator_creates_multiple_resources():
    sim = FakeAwsSimulator(region="us-east-1")
    sim.start()
    resources = sim.provision([
        {"type": "aws_s3_bucket", "name": "static-assets"},
        {"type": "aws_s3_bucket", "name": "cdn-logs"},
        {
            "type": "aws_dynamodb_table",
            "name": "sessions",
            "hash_key": "token",
            "billing_mode": "PAY_PER_REQUEST",
        },
    ])
    sim.stop()

    assert len(resources) == 3
    types = [r["type"] for r in resources]
    assert types.count("aws_s3_bucket") == 2
    assert types.count("aws_dynamodb_table") == 1

def test_simulator_unsupported_resource_type_raises():
    sim = FakeAwsSimulator(region="us-east-1")
    sim.start()
    with pytest.raises(ValueError, match="Unsupported resource type"):
        sim.provision([{"type": "aws_lambda_function"}])
    sim.stop()

def test_simulator_known_resource_types():
    assert "aws_s3_bucket" in RESOURCE_TYPES
    assert "aws_dynamodb_table" in RESOURCE_TYPES
    assert "aws_iam_role" in RESOURCE_TYPES