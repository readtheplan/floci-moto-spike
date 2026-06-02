"""floci API — HTTP wrapper around the Moto-based AWS simulator.

Deploy:  uvicorn server:app --host 127.0.0.1 --port 8080
Proxy:   nginx → proxy_pass http://127.0.0.1:8080
TLS:     Cloudflare (orange cloud) → droplet IP, Free edge cert
"""

from fastapi import FastAPI, HTTPException, Query
from floci_cli.scenarios import SCENARIOS
from floci_cli.simulator import FakeAwsSimulator
from floci_cli.plan_generator import generate_plan_json

app = FastAPI(
    title="floci-api",
    version="0.2.0",
    description="Generate realistic terraform show -json output from Moto-provisioned AWS resources",
)

# ── Health ──────────────────────────────────────────────────────────────


@app.get("/health")
async def health():
    return {"status": "ok", "scenarios": len(SCENARIOS), "region": "us-east-1"}


# ── Scenarios ───────────────────────────────────────────────────────────


@app.get("/scenarios")
async def list_scenarios():
    return {
        name: {
            "description": s["description"],
            "resource_count": len(s["resources"]),
            "has_updates": "updated_resources" in s,
        }
        for name, s in SCENARIOS.items()
    }


# ── Create (provision + return terraform plan JSON) ─────────────────────


@app.post("/create")
async def create(scenario: str = Query("mixed", description="Scenario name")):
    """Provision resources via Moto and return a 'create' terraform plan JSON."""
    spec = SCENARIOS.get(scenario)
    if not spec:
        raise HTTPException(
            400,
            f"Unknown scenario '{scenario}'. Available: {', '.join(SCENARIOS)}",
        )

    sim = FakeAwsSimulator(region="us-east-1")
    sim.start()
    try:
        resources = sim.provision(spec["resources"])
    finally:
        sim.stop()

    return generate_plan_json(before=[], after=resources, action="create")


# ── Destroy (fake before state, return delete plan) ─────────────────────


@app.post("/destroy")
async def destroy(scenario: str = Query("simple", description="Scenario name")):
    """Return a 'destroy' terraform plan JSON for a scenario."""
    spec = SCENARIOS.get(scenario)
    if not spec:
        raise HTTPException(
            400,
            f"Unknown scenario '{scenario}'. Available: {', '.join(SCENARIOS)}",
        )

    sim = FakeAwsSimulator(region="us-east-1")
    sim.start()
    try:
        resources = sim.provision(spec["resources"])
    finally:
        sim.stop()

    return generate_plan_json(before=resources, after=[], action="destroy")


# ── Update (provision before + after, return update plan with diffs) ────


@app.post("/update")
async def update(scenario: str = Query("update", description="Scenario with updated_resources")):
    """Provision before/after state and return an 'update' terraform plan JSON."""
    spec = SCENARIOS.get(scenario)
    if not spec:
        raise HTTPException(
            400,
            f"Unknown scenario '{scenario}'. Available: {', '.join(SCENARIOS)}",
        )
    if "updated_resources" not in spec:
        raise HTTPException(
            400,
            f"Scenario '{scenario}' has no 'updated_resources' — cannot generate update plan. "
            f"Try: update, or use /create or /destroy endpoints.",
        )

    # Provision initial state → "before"
    sim_before = FakeAwsSimulator(region="us-east-1")
    sim_before.start()
    try:
        before_state = sim_before.provision(spec["resources"])
    finally:
        sim_before.stop()

    # Provision modified state → "after"
    sim_after = FakeAwsSimulator(region="us-east-1")
    sim_after.start()
    try:
        after_state = sim_after.provision(spec["updated_resources"])
    finally:
        sim_after.stop()

    return generate_plan_json(before=before_state, after=after_state, action="update")
