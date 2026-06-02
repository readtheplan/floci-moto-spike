#!/usr/bin/env python3
"""floci-cli — Fake AWS resource simulator that outputs Terraform plan JSON.

Usage:
    floci-cli create --scenario simple          # provision + output plan JSON
    floci-cli destroy --scenario simple         # output destroy plan JSON
    floci-cli update --scenario update          # provision, modify, output update plan
    floci-cli list-scenarios                   # list available scenarios
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import click

from floci_cli.plan_generator import generate_plan_json
from floci_cli.scenarios import SCENARIOS
from floci_cli.simulator import FakeAwsSimulator


@click.group()
def cli() -> None:
    """Fake AWS resource simulator — generates Terraform plan JSON."""


@cli.command()
@click.option("--scenario", required=True, help="Scenario name (see list-scenarios)")
@click.option("--output", "-o", type=click.Path(path_type=Path), help="Write plan JSON to file instead of stdout")
def create(scenario: str, output: Path | None) -> None:
    """Provision fake AWS resources and output a 'create' plan JSON."""
    if scenario not in SCENARIOS:
        click.echo(
            f"Unknown scenario: {scenario}. Available: {', '.join(SCENARIOS)}",
            err=True,
        )
        raise SystemExit(1)

    spec = SCENARIOS[scenario]
    sim = FakeAwsSimulator(region="us-east-1")
    sim.start()
    try:
        resources = sim.provision(spec["resources"])
    finally:
        sim.stop()

    plan = generate_plan_json(before=[], after=resources, action="create")
    _output(plan, output)


@cli.command()
@click.option("--scenario", required=True, help="Scenario name (see list-scenarios)")
@click.option("--output", "-o", type=click.Path(path_type=Path), help="Write plan JSON to file instead of stdout")
def destroy(scenario: str, output: Path | None) -> None:
    """Output a 'destroy' plan JSON for a scenario (no real provisioning)."""
    if scenario not in SCENARIOS:
        click.echo(
            f"Unknown scenario: {scenario}. Available: {', '.join(SCENARIOS)}",
            err=True,
        )
        raise SystemExit(1)

    spec = SCENARIOS[scenario]
    # Build "before" state by simulating the resources (create + capture, then stop)
    sim = FakeAwsSimulator(region="us-east-1")
    sim.start()
    try:
        resources = sim.provision(spec["resources"])
    finally:
        sim.stop()

    plan = generate_plan_json(before=resources, after=[], action="destroy")
    _output(plan, output)


@cli.command()
@click.option("--scenario", required=True, help="Scenario name (must have updated_resources)")
@click.option("--output", "-o", type=click.Path(path_type=Path), help="Write plan JSON to file instead of stdout")
def update(scenario: str, output: Path | None) -> None:
    """Provision initial state, then modified state, and output an 'update' plan JSON with before/after diffs."""
    if scenario not in SCENARIOS:
        click.echo(
            f"Unknown scenario: {scenario}. Available: {', '.join(SCENARIOS)}",
            err=True,
        )
        raise SystemExit(1)

    spec = SCENARIOS[scenario]
    if "updated_resources" not in spec:
        click.echo(
            f"Scenario '{scenario}' does not have 'updated_resources' — cannot generate update plan.",
            err=True,
        )
        raise SystemExit(1)

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

    plan = generate_plan_json(before=before_state, after=after_state, action="update")
    _output(plan, output)


@cli.command("list-scenarios")
def list_scenarios() -> None:
    """List available scenarios."""
    for name, spec in SCENARIOS.items():
        click.echo(f"  {name}: {spec['description']}")


def _output(plan: dict[str, Any], path: Path | None) -> None:
    """Write plan JSON to stdout or file."""
    if path:
        with open(path, "w") as f:
            json.dump(plan, f, indent=2)
        click.echo(f"Plan written to {path}", err=True)
    else:
        json.dump(plan, sys.stdout, indent=2)
        sys.stdout.write("\n")


if __name__ == "__main__":
    cli()
