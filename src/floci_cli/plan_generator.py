"""Generate realistic terraform plan -json output from resource state."""
from __future__ import annotations

from typing import Any

TERRAFORM_VERSION = "1.5.7"
FORMAT_VERSION = "1.2"

def generate_plan_json(
    before: list[dict[str, Any]],
    after: list[dict[str, Any]],
    action: str = "create",
) -> dict[str, Any]:
    """Build a terraform plan -json structure from before/after resource state.

    Args:
        before: Resources that existed before the operation.
        after: Resources that exist after the operation.
        action: One of "create", "destroy", or "noop".
    """
    resource_changes: list[dict[str, Any]] = []
    action_map = {
        "create": ["create"],
        "destroy": ["delete"],
        "noop": ["no-op"],
    }
    tf_actions = action_map.get(action, ["no-op"])

    # Build a simple diff: after_set - before_set = created, before_set - after_set = destroyed
    before_addrs = {r["address"] for r in before}
    after_addrs = {r["address"] for r in after}

    if action == "create":
        resources = after
    elif action == "destroy":
        resources = before
    else:
        resources = after  # noop — use after for unchanged resources

    for res in resources:
        before_vals: dict[str, Any] | None = None
        after_vals: dict[str, Any] | None = None

        if action == "create":
            before_vals = None
            after_vals = res["attributes"]
        elif action == "destroy":
            before_vals = res["attributes"]
            after_vals = None
        else:
            before_vals = res["attributes"]
            after_vals = res["attributes"]

        resource_changes.append({
            "address": res["address"],
            "module_address": "",
            "mode": "managed",
            "type": res["type"],
            "name": res["address"].split(".", 1)[1],
            "provider_name": "registry.terraform.io/hashicorp/aws",
            "change": {
                "actions": tf_actions,
                "before": before_vals,
                "after": after_vals,
                "before_sensitive": False,
                "after_sensitive": False,
                "after_unknown": {},
                "replace_paths": [],
            },
            "action_reason": action,
        })

    return {
        "format_version": FORMAT_VERSION,
        "terraform_version": TERRAFORM_VERSION,
        "variables": {},
        "resource_changes": resource_changes,
        "resource_drift": [],
        "output_changes": {},
        "prior_state": None,
        "planned_values": {},
        "configuration": {},
        "relevant_attributes": [],
    }