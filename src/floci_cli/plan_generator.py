"""Generate Terraform plan JSON from simulator state."""
from typing import Any
import json


def generate_plan_json(resources: list[dict[str, Any]], before: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Generate a terraform show -json style plan."""
    plan = {
        "format_version": "1.2",
        "terraform_version": "1.9.0",
        "planned_values": {"root_module": {"resources": []}},
        "resource_changes": [],
        "configuration": {},
    }

    for res in resources:
        addr = f"{res['type']}.{res['name']}"
        change = {
            "address": addr,
            "mode": "managed",
            "type": res["type"],
            "name": res["name"],
            "provider_name": "registry.terraform.io/hashicorp/aws",
            "change": {
                "actions": ["create"],
                "before": None,
                "after": res["attributes"],
                "after_unknown": {},
            },
        }
        plan["resource_changes"].append(change)
        plan["planned_values"]["root_module"]["resources"].append({
            "address": addr,
            "mode": "managed",
            "type": res["type"],
            "name": res["name"],
            "provider_name": "registry.terraform.io/hashicorp/aws",
            "values": res["attributes"],
        })

    return plan
