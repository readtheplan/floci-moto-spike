#!/usr/bin/env bash
# CI script: floci create + readtheplan analyze for SOC2 compliance
# Zero Docker dependency — pure Python (moto + boto3 + click)
# Usage: ./ci/run_ci.sh [scenario]
# Default scenario: mixed (5 resources across KMS, Lambda, ALB, SG, CloudWatch)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_PYTHON="$PROJECT_DIR/.venv/bin/python"
FLOCI="$PROJECT_DIR/.venv/bin/floci"
SCENARIO="${1:-mixed}"

echo "=== floci-moto-spike CI ==="
echo "Scenario: $SCENARIO"
echo "Project:  $PROJECT_DIR"
echo ""

# Step 1: Verify floci CLI works
echo "--- [1/4] Testing floci CLI ---"
"$FLOCI" list-scenarios

# Step 2: Run full test suite
echo ""
echo "--- [2/4] Running pytest ---"
"$VENV_PYTHON" -m pytest "$PROJECT_DIR/tests/" -v

# Step 3: Generate plan JSON
echo ""
echo "--- [3/4] Generating plan JSON for scenario '$SCENARIO' ---"
PLAN_FILE="$(mktemp /tmp/floci-plan-XXXXXX.json)"
"$FLOCI" create --scenario "$SCENARIO" --output "$PLAN_FILE"
echo "Plan written to $PLAN_FILE"
echo "Plan size: $(wc -c < "$PLAN_FILE") bytes"
echo "Resource changes: $("$VENV_PYTHON" -c "import json; print(len(json.load(open('$PLAN_FILE'))['resource_changes']))")"

# Step 4: Analyze with readtheplan (SOC2 framework)
echo ""
echo "--- [4/4] readtheplan analyze (SOC2) ---"
if command -v readtheplan &>/dev/null; then
    readtheplan analyze --format json --framework soc2 "$PLAN_FILE"
    echo "readtheplan analysis complete ✓"
else
    echo "WARNING: readtheplan not found in PATH — skipping analysis"
    echo "Install: cd /root/Documents/coding/readtheplan && pip install -e ."
fi

echo ""
echo "=== CI complete ✓ ==="
echo "Plan file: $PLAN_FILE"
