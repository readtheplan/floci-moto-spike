"""Tests for floci_cli.simulator — the Moto-based fake AWS engine."""
import pytest
from floci_cli.simulator import FakeAwsSimulator, RESOURCE_TYPES

# --- Original 6 tests (must still pass) ---

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
        sim.provision([{"type": "aws_nonexistent_type"}])
    sim.stop()

def test_simulator_known_resource_types():
    assert "aws_s3_bucket" in RESOURCE_TYPES
    assert "aws_dynamodb_table" in RESOURCE_TYPES
    assert "aws_iam_role" in RESOURCE_TYPES

# --- New resource type tests (8 new) ---

def test_simulator_creates_kms_key():
    sim = FakeAwsSimulator(region="us-east-1")
    sim.start()
    resources = sim.provision([
        {"type": "aws_kms_key", "name": "my-key", "description": "Test KMS key"},
    ])
    sim.stop()

    assert len(resources) == 1
    assert resources[0]["type"] == "aws_kms_key"
    attrs = resources[0]["attributes"]
    assert attrs["alias"] == "my-key"
    assert attrs["key_id"] != ""
    assert attrs["description"] == "Test KMS key"

def test_simulator_creates_db_instance():
    sim = FakeAwsSimulator(region="us-east-1")
    sim.start()
    resources = sim.provision([
        {
            "type": "aws_db_instance",
            "name": "my-db",
            "engine": "postgres",
            "instance_class": "db.t3.micro",
            "allocated_storage": 20,
        },
    ])
    sim.stop()

    assert len(resources) == 1
    assert resources[0]["type"] == "aws_db_instance"
    attrs = resources[0]["attributes"]
    assert attrs["identifier"] == "my-db"
    assert attrs["engine"] == "postgres"
    assert attrs["instance_class"] == "db.t3.micro"

def test_simulator_creates_lambda_function():
    sim = FakeAwsSimulator(region="us-east-1")
    sim.start()
    resources = sim.provision([
        {
            "type": "aws_lambda_function",
            "name": "my-func",
            "runtime": "python3.11",
            "handler": "index.handler",
        },
    ])
    sim.stop()

    assert len(resources) == 1
    assert resources[0]["type"] == "aws_lambda_function"
    attrs = resources[0]["attributes"]
    assert attrs["function_name"] == "my-func"
    assert attrs["runtime"] == "python3.11"
    assert attrs["memory_size"] == 128

def test_simulator_creates_lb():
    sim = FakeAwsSimulator(region="us-east-1")
    sim.start()
    resources = sim.provision([
        {
            "type": "aws_lb",
            "name": "my-alb",
            "scheme": "internet-facing",
            "lb_type": "application",
        },
    ])
    sim.stop()

    assert len(resources) == 1
    assert resources[0]["type"] == "aws_lb"
    attrs = resources[0]["attributes"]
    assert attrs["name"] == "my-alb"
    assert attrs["scheme"] == "internet-facing"
    assert attrs["type"] == "application"

def test_simulator_creates_ecs_service():
    sim = FakeAwsSimulator(region="us-east-1")
    sim.start()
    resources = sim.provision([
        {
            "type": "aws_ecs_service",
            "name": "my-svc",
            "cluster": "default",
            "task_definition": "app-task:1",
            "desired_count": 2,
        },
    ])
    sim.stop()

    assert len(resources) == 1
    assert resources[0]["type"] == "aws_ecs_service"
    attrs = resources[0]["attributes"]
    assert attrs["name"] == "my-svc"
    assert attrs["cluster"] == "default"
    assert attrs["desired_count"] == 2

def test_simulator_creates_security_group():
    sim = FakeAwsSimulator(region="us-east-1")
    sim.start()
    resources = sim.provision([
        {
            "type": "aws_security_group",
            "name": "my-sg",
            "description": "Test SG",
            "vpc_id": "vpc-test123",
        },
    ])
    sim.stop()

    assert len(resources) == 1
    assert resources[0]["type"] == "aws_security_group"
    attrs = resources[0]["attributes"]
    assert attrs["name"] == "my-sg"
    assert attrs["description"] == "Test SG"
    assert attrs["group_id"] != ""

def test_simulator_creates_route53_zone():
    sim = FakeAwsSimulator(region="us-east-1")
    sim.start()
    resources = sim.provision([
        {
            "type": "aws_route53_zone",
            "name": "example.com",
            "comment": "Test zone",
        },
    ])
    sim.stop()

    assert len(resources) == 1
    assert resources[0]["type"] == "aws_route53_zone"
    attrs = resources[0]["attributes"]
    assert attrs["name"] == "example.com"
    assert attrs["zone_id"] != ""

def test_simulator_creates_cloudwatch_log_group():
    sim = FakeAwsSimulator(region="us-east-1")
    sim.start()
    resources = sim.provision([
        {
            "type": "aws_cloudwatch_log_group",
            "name": "/aws/lambda/my-func",
            "retention_in_days": 14,
        },
    ])
    sim.stop()

    assert len(resources) == 1
    assert resources[0]["type"] == "aws_cloudwatch_log_group"
    attrs = resources[0]["attributes"]
    assert attrs["name"] == "/aws/lambda/my-func"
    assert attrs["retention_in_days"] == 14

def test_simulator_all_new_resource_types_registered():
    """Verify all 8 new types are in RESOURCE_TYPES."""
    expected = [
        "aws_kms_key", "aws_db_instance", "aws_lambda_function",
        "aws_lb", "aws_ecs_service", "aws_security_group",
        "aws_route53_zone", "aws_cloudwatch_log_group",
    ]
    for rt in expected:
        assert rt in RESOURCE_TYPES, f"{rt} missing from RESOURCE_TYPES"

def test_simulator_creates_mixed_type_resources():
    """Provision multiple different new resource types in one call."""
    sim = FakeAwsSimulator(region="us-east-1")
    sim.start()
    resources = sim.provision([
        {"type": "aws_kms_key", "name": "app-key"},
        {"type": "aws_lambda_function", "name": "my-lambda", "runtime": "python3.12"},
        {"type": "aws_cloudwatch_log_group", "name": "/aws/test/log", "retention_in_days": 7},
    ])
    sim.stop()

    assert len(resources) == 3
    types = [r["type"] for r in resources]
    assert "aws_kms_key" in types
    assert "aws_lambda_function" in types
    assert "aws_cloudwatch_log_group" in types
