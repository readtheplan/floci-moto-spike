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
        timeout=15,
        cwd=str(PROJECT_ROOT),
    )

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