"""Tests for floci_cli.plan_generator — Terraform plan JSON output."""
import json
from floci_cli.plan_generator import generate_plan_json, _detect_changed_keys

# --- Original 6 tests (must still pass) ---

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

# --- New update-in-place diff tests (7 new) ---

def test_update_action_produces_update_actions():
    """When attributes change but same address, should produce ['update']."""
    plan = generate_plan_json(
        before=[
            {
                "type": "aws_kms_key",
                "address": "aws_kms_key.my-key",
                "attributes": {"alias": "my-key", "description": "Old desc", "region": "us-east-1"},
            },
        ],
        after=[
            {
                "type": "aws_kms_key",
                "address": "aws_kms_key.my-key",
                "attributes": {"alias": "my-key", "description": "New desc", "region": "us-east-1"},
            },
        ],
        action="update",
    )

    assert len(plan["resource_changes"]) == 1
    rc = plan["resource_changes"][0]
    assert rc["change"]["actions"] == ["update"]
    assert rc["change"]["before"]["description"] == "Old desc"
    assert rc["change"]["after"]["description"] == "New desc"
    assert "description" in rc["change"]["replace_paths"]

def test_update_with_no_changes_is_noop():
    """When before==after in update mode, should produce no-op."""
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
        action="update",
    )

    assert len(plan["resource_changes"]) == 1
    rc = plan["resource_changes"][0]
    assert rc["change"]["actions"] == ["no-op"]

def test_update_with_new_resource_produces_create():
    """Resource in after but not in before → create."""
    plan = generate_plan_json(
        before=[
            {
                "type": "aws_s3_bucket",
                "address": "aws_s3_bucket.old-bucket",
                "attributes": {"bucket": "old-bucket", "region": "us-east-1"},
            },
        ],
        after=[
            {
                "type": "aws_s3_bucket",
                "address": "aws_s3_bucket.old-bucket",
                "attributes": {"bucket": "old-bucket", "region": "us-east-1"},
            },
            {
                "type": "aws_s3_bucket",
                "address": "aws_s3_bucket.new-bucket",
                "attributes": {"bucket": "new-bucket", "region": "us-east-1"},
            },
        ],
        action="update",
    )

    assert len(plan["resource_changes"]) == 2
    actions_by_addr = {rc["address"]: rc["change"]["actions"] for rc in plan["resource_changes"]}
    assert actions_by_addr["aws_s3_bucket.old-bucket"] == ["no-op"]
    assert actions_by_addr["aws_s3_bucket.new-bucket"] == ["create"]

def test_update_with_removed_resource_produces_delete():
    """Resource in before but not in after → delete."""
    plan = generate_plan_json(
        before=[
            {
                "type": "aws_s3_bucket",
                "address": "aws_s3_bucket.stale",
                "attributes": {"bucket": "stale", "region": "us-east-1"},
            },
            {
                "type": "aws_s3_bucket",
                "address": "aws_s3_bucket.kept",
                "attributes": {"bucket": "kept", "region": "us-east-1"},
            },
        ],
        after=[
            {
                "type": "aws_s3_bucket",
                "address": "aws_s3_bucket.kept",
                "attributes": {"bucket": "kept", "region": "us-east-1"},
            },
        ],
        action="update",
    )

    assert len(plan["resource_changes"]) == 2
    actions_by_addr = {rc["address"]: rc["change"]["actions"] for rc in plan["resource_changes"]}
    assert actions_by_addr["aws_s3_bucket.stale"] == ["delete"]
    assert actions_by_addr["aws_s3_bucket.kept"] == ["no-op"]

def test_update_mixed_actions():
    """Update, create, destroy, noop all in one plan."""
    plan = generate_plan_json(
        before=[
            {
                "type": "aws_s3_bucket",
                "address": "aws_s3_bucket.changed",
                "attributes": {"bucket": "changed", "region": "us-east-1"},
            },
            {
                "type": "aws_s3_bucket",
                "address": "aws_s3_bucket.removed",
                "attributes": {"bucket": "removed", "region": "us-east-1"},
            },
            {
                "type": "aws_s3_bucket",
                "address": "aws_s3_bucket.unchanged",
                "attributes": {"bucket": "unchanged", "region": "us-east-1"},
            },
        ],
        after=[
            {
                "type": "aws_s3_bucket",
                "address": "aws_s3_bucket.changed",
                "attributes": {"bucket": "changed-v2", "region": "us-east-1"},
            },
            {
                "type": "aws_s3_bucket",
                "address": "aws_s3_bucket.unchanged",
                "attributes": {"bucket": "unchanged", "region": "us-east-1"},
            },
            {
                "type": "aws_s3_bucket",
                "address": "aws_s3_bucket.added",
                "attributes": {"bucket": "added", "region": "us-east-1"},
            },
        ],
        action="update",
    )

    assert len(plan["resource_changes"]) == 4
    actions_by_addr = {rc["address"]: rc["change"]["actions"] for rc in plan["resource_changes"]}
    assert actions_by_addr["aws_s3_bucket.changed"] == ["update"]
    assert actions_by_addr["aws_s3_bucket.removed"] == ["delete"]
    assert actions_by_addr["aws_s3_bucket.unchanged"] == ["no-op"]
    assert actions_by_addr["aws_s3_bucket.added"] == ["create"]

def test_detect_changed_keys_identifies_differences():
    """_detect_changed_keys returns list of keys that differ."""
    old = {"a": 1, "b": "hello", "c": True}
    new = {"a": 1, "b": "world", "c": True}
    changed = _detect_changed_keys(old, new)
    assert changed == ["b"]

def test_detect_changed_keys_handles_none():
    assert _detect_changed_keys(None, {"a": 1}) == []
    assert _detect_changed_keys({"a": 1}, None) == []
    assert _detect_changed_keys(None, None) == []
