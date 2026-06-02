"""Integration test: full pipeline and readtheplan compatibility."""
import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CLI_SCRIPT = str(PROJECT_ROOT / "src" / "floci_cli" / "cli.py")

def test_full_create_pipeline_produces_valid_plan():
    """Run floci-cli create, verify plan structure matches readtheplan expectations."""
    result = subprocess.run(
        [sys.executable, CLI_SCRIPT, "create", "--scenario", "simple"],
        capture_output=True, text=True, timeout=15,
        cwd=str(PROJECT_ROOT),
    )
    assert result.returncode == 0, f"CLI failed: {result.stderr}"

    plan = json.loads(result.stdout)

    # readtheplan compatibility checks
    assert plan["format_version"] == "1.2"
    assert "resource_changes" in plan, "readtheplan requires resource_changes"
    assert len(plan["resource_changes"]) >= 1, "Plan must have at least one change"

    for rc in plan["resource_changes"]:
        assert rc.get("address"), "Every resource_change needs an address"
        assert rc.get("type", "").startswith("aws_"), "Must be an AWS resource type"
        assert "change" in rc, "Every resource_change needs a change block"
        assert rc["change"].get("actions"), "Change must have actions"

    # Verify we have 3 resource types across the plan
    resource_types = {rc["type"] for rc in plan["resource_changes"]}
    assert "aws_s3_bucket" in resource_types
    assert "aws_dynamodb_table" in resource_types
    assert "aws_iam_role" in resource_types

def test_full_destroy_pipeline_produces_valid_plan():
    result = subprocess.run(
        [sys.executable, CLI_SCRIPT, "destroy", "--scenario", "simple"],
        capture_output=True, text=True, timeout=15,
        cwd=str(PROJECT_ROOT),
    )
    assert result.returncode == 0, f"CLI failed: {result.stderr}"

    plan = json.loads(result.stdout)
    for rc in plan["resource_changes"]:
        assert rc["change"]["actions"] == ["delete"], f"Destroy plan should have only delete actions: {rc}"

def test_output_to_file_produces_readable_json():
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        outpath = Path(f.name)

    try:
        result = subprocess.run(
            [sys.executable, CLI_SCRIPT, "create", "--scenario", "full", "--output", str(outpath)],
            capture_output=True, text=True, timeout=15,
            cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 0

        with open(outpath) as f:
            plan = json.load(f)
        assert len(plan["resource_changes"]) == 7
    finally:
        outpath.unlink()