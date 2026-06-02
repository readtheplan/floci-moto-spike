"""Floci CLI - Fake AWS resource simulator."""
import json
import click
from .simulator import FakeAwsSimulator
from .plan_generator import generate_plan_json

@click.group()
def cli():
    """Floci - Minimal fake AWS simulator for readtheplan testing."""
    pass

@cli.command()
@click.option("--scenario", default="simple", help="Scenario to run (simple/full)")
@click.option("--output", default="plan.json", help="Output file for Terraform plan JSON")
def create(scenario: str, output: str):
    """Create fake resources and output a Terraform plan JSON."""
    sim = FakeAwsSimulator()

    if scenario == "simple":
        resources = [
            {"type": "aws_s3_bucket", "name": "logs-bucket"},
            {"type": "aws_iam_role", "name": "lambda-role"},
        ]
    else:
        resources = [
            {"type": "aws_s3_bucket", "name": "logs-bucket"},
            {"type": "aws_dynamodb_table", "name": "users", "hash_key": "id"},
            {"type": "aws_iam_role", "name": "lambda-role"},
        ]

    sim.start()
    created = sim.provision(resources)
    sim.stop()

    plan = generate_plan_json(created)
    with open(output, "w") as f:
        json.dump(plan, f, indent=2)

    click.echo(f"Created {len(created)} resources. Plan written to {output}")

@cli.command()
def list_scenarios():
    """List available scenarios."""
    click.echo("Available scenarios: simple, full")

if __name__ == "__main__":
    cli()
