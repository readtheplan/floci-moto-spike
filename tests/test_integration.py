"""Integration test: full pipeline and readtheplan compatibility."""
import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CLI_SCRIPT = str(PROJECT_ROOT / "src" / "floci_cli" / "cli.py")

# --- Original 3 tests (must still pass) ---

def test_full_create_pipeline_produces_valid_plan():
    """Run floci-cli create, verify plan structure matches readtheplan expectations."""
    result = subprocess.run(
        [sys.executable, CLI_SCRIPT, "create", "--scenario", "simple"],
        capture_output=True, text=True, timeout=30,
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
        capture_output=True, text=True, timeout=30,
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
            capture_output=True, text=True, timeout=30,
            cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 0

        with open(outpath) as f:
            plan = json.load(f)
        assert len(plan["resource_changes"]) == 7
    finally:
        outpath.unlink()

# --- New integration tests (6 new) ---

def test_mixed_scenario_produces_valid_plan():
    """Mixed scenario with 5 diverse resource types."""
    result = subprocess.run(
        [sys.executable, CLI_SCRIPT, "create", "--scenario", "mixed"],
        capture_output=True, text=True, timeout=30,
        cwd=str(PROJECT_ROOT),
    )
    assert result.returncode == 0, f"CLI failed: {result.stderr}"

    plan = json.loads(result.stdout)
    assert plan["format_version"] == "1.2"
    assert len(plan["resource_changes"]) == 5

    for rc in plan["resource_changes"]:
        assert rc.get("address")
        assert rc.get("type", "").startswith("aws_")
        assert "change" in rc
        assert rc["change"].get("actions") == ["create"]

def test_security_scenario_produces_valid_plan():
    """Security scenario with 3 SGs, 2 roles, 1 KMS key."""
    result = subprocess.run(
        [sys.executable, CLI_SCRIPT, "create", "--scenario", "security"],
        capture_output=True, text=True, timeout=30,
        cwd=str(PROJECT_ROOT),
    )
    assert result.returncode == 0, f"CLI failed: {result.stderr}"

    plan = json.loads(result.stdout)
    assert len(plan["resource_changes"]) == 6
    sg_count = sum(1 for rc in plan["resource_changes"] if rc["type"] == "aws_security_group")
    assert sg_count == 3

def test_update_pipeline_produces_valid_diff_plan():
    """Update scenario — verify before/after diffs in plan JSON."""
    result = subprocess.run(
        [sys.executable, CLI_SCRIPT, "update", "--scenario", "update"],
        capture_output=True, text=True, timeout=30,
        cwd=str(PROJECT_ROOT),
    )
    assert result.returncode == 0, f"CLI failed: {result.stderr}"

    plan = json.loads(result.stdout)
    assert plan["format_version"] == "1.2"
    assert len(plan["resource_changes"]) == 3

    for rc in plan["resource_changes"]:
        assert rc.get("address")
        assert "change" in rc
        # Each change should have before and after (not None for update/noop)
        change = rc["change"]
        if change["actions"] in [["update"], ["no-op"]]:
            assert change.get("before") is not None, f"Expected before for {rc['address']}"
            assert change.get("after") is not None, f"Expected after for {rc['address']}"

def test_readtheplan_compatibility_mixed():
    """Verify readtheplan can parse the mixed scenario plan."""
    with subprocess.Popen(
        [sys.executable, CLI_SCRIPT, "create", "--scenario", "mixed"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        cwd=str(PROJECT_ROOT),
    ) as proc:
        stdout, stderr = proc.communicate(timeout=30)
        assert proc.returncode == 0, f"CLI failed: {stderr.decode()}"

    plan = json.loads(stdout)
    # readtheplan structural checks
    assert plan["format_version"] == "1.2"
    assert isinstance(plan.get("resource_changes"), list)
    for rc in plan["resource_changes"]:
        assert "address" in rc
        assert "type" in rc
        assert "change" in rc
        assert "actions" in rc["change"]

def test_plan_json_roundtrip_file():
    """Write plan to file and read back — verify integrity."""
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        outpath = Path(f.name)

    try:
        result = subprocess.run(
            [sys.executable, CLI_SCRIPT, "create", "--scenario", "mixed", "--output", str(outpath)],
            capture_output=True, text=True, timeout=30,
            cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 0

        with open(outpath) as f:
            plan = json.load(f)
        assert len(plan["resource_changes"]) == 5
        assert plan["format_version"] == "1.2"
    finally:
        outpath.unlink()

def test_destroy_full_scenario():
    """Destroy full scenario — verify all are delete actions."""
    result = subprocess.run(
        [sys.executable, CLI_SCRIPT, "destroy", "--scenario", "full"],
        capture_output=True, text=True, timeout=30,
        cwd=str(PROJECT_ROOT),
    )
    assert result.returncode == 0, f"CLI failed: {result.stderr}"

    plan = json.loads(result.stdout)
    assert len(plan["resource_changes"]) == 7
    for rc in plan["resource_changes"]:
        assert rc["change"]["actions"] == ["delete"]
