"""floci API route handlers — health, scenarios, create, destroy, update."""

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse, RedirectResponse

from floci_cli.scenarios import SCENARIOS
from floci_cli.simulator import FakeAwsSimulator
from floci_cli.plan_generator import generate_plan_json

from .cache import plan_cache
from .middleware import limiter

router = APIRouter()


# ── Friendly root — redirect to Swagger docs ────────────────────────────

@router.get("/", include_in_schema=False)
async def root(request: Request):
    """Redirect root to the interactive API docs (Swagger UI)."""
    return RedirectResponse(url="/docs", status_code=302)


# ── Health ──────────────────────────────────────────────────────────────

@router.get("/health")
@limiter.limit("120/minute")
async def health(request: Request) -> JSONResponse:
    data = {
        "status": "ok",
        "scenarios": len(SCENARIOS),
        "region": "us-east-1",
        "cache": plan_cache.stats(),
    }
    return JSONResponse(content=data)


# ── Scenarios ───────────────────────────────────────────────────────────

@router.get("/scenarios")
@limiter.limit("60/minute")
async def list_scenarios(request: Request) -> JSONResponse:
    data = {
        name: {
            "description": s["description"],
            "resource_count": len(s["resources"]),
            "has_updates": "updated_resources" in s,
        }
        for name, s in SCENARIOS.items()
    }
    return JSONResponse(content=data)


# ── Create (provision + return terraform plan JSON) ─────────────────────

@router.post("/create")
@limiter.limit("30/minute")
async def create(
    request: Request,
    scenario: str = Query("mixed", description="Scenario name: simple, full, mixed, security, update"),
) -> JSONResponse:
    """Provision resources via Moto and return a 'create' terraform plan JSON."""
    if scenario not in SCENARIOS:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "unknown_scenario",
                "requested": scenario,
                "available": list(SCENARIOS.keys()),
                "hint": "GET /scenarios for details on each.",
            },
        )

    # Check cache first
    cached = plan_cache.get("create", scenario, "create")
    if cached is not None:
        return JSONResponse(
            content=cached,
            headers={"X-Cache": "HIT", "Cache-Control": f"public, max-age={plan_cache._ttl}"},
        )

    spec = SCENARIOS[scenario]
    sim = FakeAwsSimulator(region="us-east-1")
    sim.start()
    try:
        resources = sim.provision(spec["resources"])
    finally:
        sim.stop()

    result = generate_plan_json(before=[], after=resources, action="create")
    plan_cache.set("create", scenario, "create", result)

    return JSONResponse(
        content=result,
        headers={"X-Cache": "MISS", "Cache-Control": f"public, max-age={plan_cache._ttl}"},
    )


# ── Destroy ─────────────────────────────────────────────────────────────

@router.post("/destroy")
@limiter.limit("30/minute")
async def destroy(
    request: Request,
    scenario: str = Query("simple", description="Scenario name"),
) -> JSONResponse:
    """Return a 'destroy' terraform plan JSON for a scenario."""
    if scenario not in SCENARIOS:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "unknown_scenario",
                "requested": scenario,
                "available": list(SCENARIOS.keys()),
            },
        )

    cached = plan_cache.get("destroy", scenario, "destroy")
    if cached is not None:
        return JSONResponse(
            content=cached,
            headers={"X-Cache": "HIT", "Cache-Control": f"public, max-age={plan_cache._ttl}"},
        )

    spec = SCENARIOS[scenario]
    sim = FakeAwsSimulator(region="us-east-1")
    sim.start()
    try:
        resources = sim.provision(spec["resources"])
    finally:
        sim.stop()

    result = generate_plan_json(before=resources, after=[], action="destroy")
    plan_cache.set("destroy", scenario, "destroy", result)

    return JSONResponse(
        content=result,
        headers={"X-Cache": "MISS", "Cache-Control": f"public, max-age={plan_cache._ttl}"},
    )


# ── Update (provision before + after) ───────────────────────────────────

@router.post("/update")
@limiter.limit("20/minute")
async def update(
    request: Request,
    scenario: str = Query("update", description="Scenario with updated_resources"),
) -> JSONResponse:
    """Provision before/after state and return an 'update' terraform plan JSON."""
    if scenario not in SCENARIOS:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "unknown_scenario",
                "requested": scenario,
                "available": list(SCENARIOS.keys()),
            },
        )

    spec = SCENARIOS[scenario]
    if "updated_resources" not in spec:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "no_update_support",
                "message": f"Scenario '{scenario}' has no 'updated_resources' — cannot generate update plan.",
                "hint": "Try scenario=update, or use /create or /destroy endpoints.",
            },
        )

    cached = plan_cache.get("update", scenario, "update")
    if cached is not None:
        return JSONResponse(
            content=cached,
            headers={"X-Cache": "HIT", "Cache-Control": f"public, max-age={plan_cache._ttl}"},
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

    result = generate_plan_json(before=before_state, after=after_state, action="update")
    plan_cache.set("update", scenario, "update", result)

    return JSONResponse(
        content=result,
        headers={"X-Cache": "MISS", "Cache-Control": f"public, max-age={plan_cache._ttl}"},
    )
