"""Tests for floci_cli.plan_generator — Terraform plan JSON output."""
import json
from floci_cli.plan_generator import generate_plan_json

def test_plan_json_has_required_top_level_keys():
    plan = generate_plan_json(
        before=[],
        after=[
            {
                "type": "aws_s3_bucket",
                "address": "aws_s3_bucket.my-bucket",
                "attributes": {"bucket": "my-bucket", "region": "us-east-1"},
            },
        ],
        action="create",
    )

    assert plan["format_version"] == "1.2"
    assert "resource_changes" in plan
    assert "variables" in plan
    assert "terraform_version" in plan

def test_single_create_produces_one_resource_change():
    plan = generate_plan_json(
        before=[],
        after=[
            {
                "type": "aws_s3_bucket",
                "address": "aws_s3_bucket.my-bucket",
                "attributes": {"bucket": "my-bucket", "region": "us-east-1"},
            },
        ],
        action="create",
    )

    assert len(plan["resource_changes"]) == 1
    rc = plan["resource_changes"][0]
    assert rc["address"] == "aws_s3_bucket.my-bucket"
    assert rc["type"] == "aws_s3_bucket"
    assert rc["change"]["actions"] == ["create"]

def test_destroy_produces_delete_action():
    plan = generate_plan_json(
        before=[
            {
                "type": "aws_s3_bucket",
                "address": "aws_s3_bucket.my-bucket",
                "attributes": {"bucket": "my-bucket", "region": "us-east-1"},
            },
        ],
        after=[],
        action="destroy",
    )

    assert len(plan["resource_changes"]) == 1
    rc = plan["resource_changes"][0]
    assert rc["change"]["actions"] == ["delete"]

def test_noop_produces_noop_action():
    plan = generate_plan_json(
        before=[
            {
                "type": "aws_s3_bucket",
                "address": "aws_s3_bucket.my-bucket",
                "attributes": {"bucket": "my-bucket", "region": "us-east-1"},
            },
        ],
        after=[
            {
                "type": "aws_s3_bucket",
                "address": "aws_s3_bucket.my-bucket",
                "attributes": {"bucket": "my-bucket", "region": "us-east-1"},
            },
        ],
        action="noop",
    )

    assert len(plan["resource_changes"]) == 1
    rc = plan["resource_changes"][0]
    assert rc["change"]["actions"] == ["no-op"]

def test_multiple_resource_types_in_plan():
    plan = generate_plan_json(
        before=[],
        after=[
            {
                "type": "aws_s3_bucket",
                "address": "aws_s3_bucket.logs",
                "attributes": {"bucket": "logs", "region": "us-east-1"},
            },
            {
                "type": "aws_dynamodb_table",
                "address": "aws_dynamodb_table.users",
                "attributes": {"name": "users", "hash_key": "id", "billing_mode": "PAY_PER_REQUEST", "region": "us-east-1"},
            },
            {
                "type": "aws_iam_role",
                "address": "aws_iam_role.exec",
                "attributes": {"name": "exec", "region": "us-east-1"},
            },
        ],
        action="create",
    )

    assert len(plan["resource_changes"]) == 3
    types = sorted(rc["type"] for rc in plan["resource_changes"])
    assert types == ["aws_dynamodb_table", "aws_iam_role", "aws_s3_bucket"]

def test_plan_json_is_valid_json_string():
    plan = generate_plan_json(
        before=[],
        after=[
            {
                "type": "aws_s3_bucket",
                "address": "aws_s3_bucket.my-bucket",
                "attributes": {"bucket": "my-bucket", "region": "us-east-1"},
            },
        ],
        action="create",
    )
    # verify roundtrip
    s = json.dumps(plan)
    parsed = json.loads(s)
    assert parsed == plan