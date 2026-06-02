# Floci Spike: Moto-Based Fake AWS Resource Simulator

**Spike type:** standard — validates replacing Docker-dependent Floci with pure-Python Moto.

**Question:** Can we generate realistic Terraform plan JSON for readtheplan testing using only `moto` + `boto3`, without Docker or real AWS credentials?

## Verdict: VALIDATED

### What worked

- Moto started in-process with zero-config — no Docker, no auth tokens, no credentials
- 3 resource types (S3, DynamoDB, IAM) provisioned correctly via boto3 against Moto backends
- Plan JSON output matches real `terraform show -json` format (format_version 1.2, resource_changes with address/type/change/actions)
- CLI works: `floci create --scenario full` → valid plan JSON in < 1s
- readtheplan `analyze` accepts the output and classifies risks correctly (e.g. SOC2 controls)
- 2 built-in scenarios (simple: 3 resources, full: 7 resources) — extensible
- 21 tests, all passing, no flakiness
- Integration test roundtrips the full pipeline (CLI → plan JSON → readtheplan)
- Generated plans wired into `site/playground/floci-spike-*-plan.json`

### What didn't (limitations)

- `moto` only supports resource types it has mock backends for. Adding a new type requires moto to support it (or writing a custom mock)
- No attribute diffing — the plan generator treats create/destroy as all-or-nothing; no "update in-place" diffs yet
- Plan JSON is not byte-identical to real Terraform output — it's structurally compatible but misses some Terraform boilerplate (provider_config, proposed_unknown, etc.)

### Surprises

- Moto's in-process mock pattern (`mock_aws().start()`) is incredibly simple — no Docker daemon needed
- The full flow (install moto + boto3 + click) is ~3 MiB of deps vs 13 MiB for the Floci Docker image
- Moto works in CI without Docker-in-Docker — a big win for GitHub Actions testing
- Destroy scenario works without side effects (simulates before state then generates delete plan)

### Recommendation for the real build

- **Use this for readtheplan CI testing** — replace the Floci Docker step in CI with `floci create --scenario full`. Faster startup, no Docker dependency, pure Python.
- **Extend resource type support** — add the full set of readtheplan-ruled AWS types (EC2, Lambda, ALB, SQS, SNS, KMS, etc.) as moto backends allow.
- **Add update-in-place diffs** — capture before/after state with attribute-level diffing to produce "update" actions (not just create/destroy).
- **Package as a real CLI** — publish `floci-cli` to PyPI with `pip install floci-cli` for easy CI integration (or keep as internal spike tool).
- Update `examples/07-floci-demo/` and regeneration scripts to optionally use the Python version.

## Usage (from spike dir)

```bash
cd /root/.hermes/plans/spikes/floci-moto-spike
.venv/bin/floci create --scenario simple --output /tmp/plan.json
.venv/bin/floci destroy --scenario full
.venv/bin/floci list-scenarios
```

## Files

- src/floci_cli/simulator.py — Moto provisioning for 3 types
- src/floci_cli/plan_generator.py — full before/after/action plan JSON builder
- src/floci_cli/cli.py + scenarios.py — click CLI
- tests/ — 21 TDD tests (simulator 6, plan 6, cli 6, integration 3)
- pyproject.toml with floci script entry

## Verification

- All tests: ` .venv/bin/python -m pytest tests/ -v `
- readtheplan roundtrip: `floci create ... | readtheplan analyze --framework soc2`

**Date completed:** 2026-06-02 (picked up from DeepSeek session on 2026-06-01)

**Location:** /root/.hermes/plans/spikes/floci-moto-spike

See Obsidian `02 - PROJECTS/floci-spike.md` for project tracking.