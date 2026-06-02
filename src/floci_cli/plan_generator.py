"""Generate realistic terraform plan -json output from resource state."""
from __future__ import annotations

from typing import Any

TERRAFORM_VERSION = "1.5.7"
FORMAT_VERSION = "1.2"

def _detect_changed_keys(
    before_attrs: dict[str, Any] | None,
    after_attrs: dict[str, Any] | None,
) -> list[str]:
    """Return list of top-level keys whose values differ between before and after."""
    if before_attrs is None or after_attrs is None:
        return []
    changed: list[str] = []
    all_keys = set(before_attrs.keys()) | set(after_attrs.keys())
    for key in sorted(all_keys):
        if before_attrs.get(key) != after_attrs.get(key):
            changed.append(key)
    return changed


def generate_plan_json(
    before: list[dict[str, Any]],
    after: list[dict[str, Any]],
    action: str = "create",
) -> dict[str, Any]:
    """Build a terraform plan -json structure from before/after resource state.

    Args:
        before: Resources that existed before the operation.
        after: Resources that exist after the operation.
        action: One of "create", "destroy", "noop", or "update".
                When "update", matches before/after by address and produces
                diffed resource_changes with actions=["update"].
    """
    resource_changes: list[dict[str, Any]] = []
    action_map = {
        "create": ["create"],
        "destroy": ["delete"],
        "noop": ["no-op"],
        "update": ["update"],
    }
    tf_actions = action_map.get(action, ["no-op"])

    if action == "update":
        # Match before/after by address; produce update diffs
        before_map: dict[str, dict[str, Any]] = {r["address"]: r for r in before}
        after_map: dict[str, dict[str, Any]] = {r["address"]: r for r in after}

        # Resources that existed before (may have been modified or destroyed)
        for addr, before_res in before_map.items():
            after_res = after_map.get(addr)
            before_attrs = before_res["attributes"]
            if after_res is None:
                # Resource was destroyed
                resource_changes.append({
                    "address": addr,
                    "module_address": "",
                    "mode": "managed",
                    "type": before_res["type"],
                    "name": addr.split(".", 1)[1],
                    "provider_name": "registry.terraform.io/hashicorp/aws",
                    "change": {
                        "actions": ["delete"],
                        "before": before_attrs,
                        "after": None,
                        "before_sensitive": False,
                        "after_sensitive": False,
                        "after_unknown": {},
                        "replace_paths": [],
                    },
                    "action_reason": "destroy",
                })
            else:
                after_attrs = after_res["attributes"]
                changed_keys = _detect_changed_keys(before_attrs, after_attrs)
                if changed_keys:
                    resource_changes.append({
                        "address": addr,
                        "module_address": "",
                        "mode": "managed",
                        "type": before_res["type"],
                        "name": addr.split(".", 1)[1],
                        "provider_name": "registry.terraform.io/hashicorp/aws",
                        "change": {
                            "actions": ["update"],
                            "before": before_attrs,
                            "after": after_attrs,
                            "before_sensitive": False,
                            "after_sensitive": False,
                            "after_unknown": {},
                            "replace_paths": changed_keys,
                        },
                        "action_reason": "update",
                    })
                else:
                    # No attributes changed — no-op
                    resource_changes.append({
                        "address": addr,
                        "module_address": "",
                        "mode": "managed",
                        "type": before_res["type"],
                        "name": addr.split(".", 1)[1],
                        "provider_name": "registry.terraform.io/hashicorp/aws",
                        "change": {
                            "actions": ["no-op"],
                            "before": before_attrs,
                            "after": after_attrs,
                            "before_sensitive": False,
                            "after_sensitive": False,
                            "after_unknown": {},
                            "replace_paths": [],
                        },
                        "action_reason": "noop",
                    })

        # Resources that are entirely new (in after but not in before)
        for addr, after_res in after_map.items():
            if addr not in before_map:
                resource_changes.append({
                    "address": addr,
                    "module_address": "",
                    "mode": "managed",
                    "type": after_res["type"],
                    "name": addr.split(".", 1)[1],
                    "provider_name": "registry.terraform.io/hashicorp/aws",
                    "change": {
                        "actions": ["create"],
                        "before": None,
                        "after": after_res["attributes"],
                        "before_sensitive": False,
                        "after_sensitive": False,
                        "after_unknown": {},
                        "replace_paths": [],
                    },
                    "action_reason": "create",
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

    # --- original create / destroy / noop logic ---

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
