"""Tests for floci_cli.cli — the CLI entrypoint."""
import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CLI_SCRIPT = str(PROJECT_ROOT / "src" / "floci_cli" / "cli.py")

def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, CLI_SCRIPT, *args],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=str(PROJECT_ROOT),
    )

# --- Original 6 tests (must still pass) ---

def test_cli_create_scenario_outputs_valid_plan_json():
    result = run_cli("create", "--scenario", "simple")
    assert result.returncode == 0, f"stderr: {result.stderr}"

    plan = json.loads(result.stdout)
    assert "resource_changes" in plan
    assert len(plan["resource_changes"]) > 0

def test_cli_create_with_output_file():
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        outpath = f.name

    try:
        result = run_cli("create", "--scenario", "simple", "--output", outpath)
        assert result.returncode == 0

        with open(outpath) as f:
            plan = json.load(f)
        assert "resource_changes" in plan
        assert len(plan["resource_changes"]) > 0
    finally:
        Path(outpath).unlink()

def test_cli_help():
    result = run_cli("--help")
    assert result.returncode == 0
    assert "create" in result.stdout
    assert "destroy" in result.stdout

def test_cli_destroy_scenario():
    result = run_cli("destroy", "--scenario", "simple")
    assert result.returncode == 0
    plan = json.loads(result.stdout)
    assert len(plan["resource_changes"]) > 0
    assert plan["resource_changes"][0]["change"]["actions"] == ["delete"]

def test_cli_unknown_scenario():
    result = run_cli("create", "--scenario", "nonexistent")
    assert result.returncode != 0
    assert "Unknown scenario" in result.stderr

def test_cli_list_scenarios():
    result = run_cli("list-scenarios")
    assert result.returncode == 0
    assert "simple" in result.stdout
    assert "full" in result.stdout

# --- New scenario and update command tests (7 new) ---

def test_cli_create_mixed_scenario():
    result = run_cli("create", "--scenario", "mixed")
    assert result.returncode == 0, f"stderr: {result.stderr}"

    plan = json.loads(result.stdout)
    assert len(plan["resource_changes"]) == 5
    types = {rc["type"] for rc in plan["resource_changes"]}
    assert "aws_kms_key" in types
    assert "aws_lambda_function" in types
    assert "aws_lb" in types
    assert "aws_security_group" in types
    assert "aws_cloudwatch_log_group" in types

def test_cli_create_security_scenario():
    result = run_cli("create", "--scenario", "security")
    assert result.returncode == 0, f"stderr: {result.stderr}"

    plan = json.loads(result.stdout)
    assert len(plan["resource_changes"]) == 6
    types = [rc["type"] for rc in plan["resource_changes"]]
    assert types.count("aws_security_group") == 3
    assert types.count("aws_iam_role") == 2
    assert types.count("aws_kms_key") == 1

def test_cli_update_scenario_produces_update_plan():
    result = run_cli("update", "--scenario", "update")
    assert result.returncode == 0, f"stderr: {result.stderr}"

    plan = json.loads(result.stdout)
    assert len(plan["resource_changes"]) == 3

    actions_by_addr = {}
    for rc in plan["resource_changes"]:
        actions_by_addr[rc["address"]] = rc["change"]["actions"]

    # KMS key description changed → update
    assert actions_by_addr.get("aws_kms_key.master-key") == ["update"]
    # Lambda runtime changed → update
    assert actions_by_addr.get("aws_lambda_function.worker") == ["update"]
    # S3 bucket unchanged → no-op
    assert actions_by_addr.get("aws_s3_bucket.config-bucket") == ["no-op"]

def test_cli_update_requires_updated_resources():
    """Scenarios without updated_resources should fail on update."""
    result = run_cli("update", "--scenario", "simple")
    assert result.returncode != 0
    assert "updated_resources" in result.stderr

def test_cli_list_scenarios_shows_new_scenarios():
    result = run_cli("list-scenarios")
    assert result.returncode == 0
    assert "mixed" in result.stdout
    assert "update" in result.stdout
    assert "security" in result.stdout

def test_cli_create_full_scenario():
    result = run_cli("create", "--scenario", "full")
    assert result.returncode == 0, f"stderr: {result.stderr}"

    plan = json.loads(result.stdout)
    assert len(plan["resource_changes"]) == 7

def test_cli_update_help():
    result = run_cli("update", "--help")
    assert result.returncode == 0
    assert "update" in result.stdout
