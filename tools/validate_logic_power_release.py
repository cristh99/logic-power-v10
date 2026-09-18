#!/usr/bin/env python3
"""Fail-closed validator for the Logic Power Core release manifest."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

HEX40 = re.compile(r"^[0-9a-f]{40}$")
ALLOWED_STATUS = {
    "VERIFIED_SCOPED",
    "INTERNALLY_VERIFIED",
    "INTERNAL_READINESS_808",
}
REQUIRED_COMPONENTS = {
    "logic_power_v10",
    "logic_power_problem_solver_v1",
    "logic_power_knowledge_action_loop_v1",
}
PROHIBITED_PREFIXES = (
    "tree_power_",
    "verified_power_",
    "corrigible_dynamic_power_",
    "adversarial_coalition_power_",
    "open_world_discovery_power_",
)


class ReleaseValidationError(ValueError):
    pass


def git_blob_sha(path: Path) -> str:
    if path.is_symlink():
        data = os.readlink(path).encode("utf-8")
    else:
        data = path.read_bytes()
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def git_tree_sha(path: Path) -> str:
    """Recompute a Git tree object ID from a clean checkout directory."""
    if not path.is_dir() or path.is_symlink():
        raise ReleaseValidationError(f"not a real directory: {path}")
    payload = bytearray()
    for child in sorted(path.iterdir(), key=lambda p: p.name.encode("utf-8")):
        name = child.name.encode("utf-8")
        if b"/" in name or b"\0" in name:
            raise ReleaseValidationError(f"invalid Git path name: {child.name!r}")
        if child.is_symlink():
            mode = b"120000"
            object_sha = git_blob_sha(child)
        elif child.is_dir():
            mode = b"40000"
            object_sha = git_tree_sha(child)
        elif child.is_file():
            mode = b"100755" if child.stat().st_mode & 0o111 else b"100644"
            object_sha = git_blob_sha(child)
        else:
            raise ReleaseValidationError(f"unsupported filesystem entry: {child}")
        payload.extend(mode + b" " + name + b"\0" + bytes.fromhex(object_sha))
    header = f"tree {len(payload)}\0".encode("ascii")
    return hashlib.sha1(header + bytes(payload)).hexdigest()


def _validate_sha(value: Any, field: str) -> str:
    if not isinstance(value, str) or HEX40.fullmatch(value) is None:
        raise ReleaseValidationError(f"{field} must be a lowercase 40-hex Git SHA")
    return value


def validate_manifest_data(data: dict[str, Any]) -> None:
    if data.get("schema") != "logic-power-release-manifest/1":
        raise ReleaseValidationError("unsupported manifest schema")
    if data.get("status") != "RELEASE_CANDIDATE_UNMERGED":
        raise ReleaseValidationError("release must remain an unmerged candidate")

    base = data.get("base")
    if not isinstance(base, dict):
        raise ReleaseValidationError("base object missing")
    _validate_sha(base.get("commit_sha"), "base.commit_sha")
    _validate_sha(base.get("tree_sha"), "base.tree_sha")

    constraints = data.get("constraints")
    if not isinstance(constraints, dict):
        raise ReleaseValidationError("constraints object missing")
    zero_fields = (
        "active_agent_messages",
        "existing_branches_modified",
        "workflow_files_added",
        "workflow_runs_required",
        "paid_spend_usd",
    )
    for field in zero_fields:
        if constraints.get(field) != 0:
            raise ReleaseValidationError(f"constraint {field} must be zero")
    if constraints.get("automatic_merge") is not False:
        raise ReleaseValidationError("automatic merge must be false")
    if constraints.get("production_authority") is not False:
        raise ReleaseValidationError("production authority must be false")

    components = data.get("components")
    if not isinstance(components, list):
        raise ReleaseValidationError("components must be a list")
    names = {item.get("name") for item in components if isinstance(item, dict)}
    if names != REQUIRED_COMPONENTS:
        raise ReleaseValidationError("canonical component set mismatch")

    paths: set[str] = set()
    for item in components:
        if not isinstance(item, dict):
            raise ReleaseValidationError("component must be an object")
        name = item.get("name")
        path = item.get("path")
        if path != name:
            raise ReleaseValidationError(f"component path mismatch: {name}")
        if path in paths:
            raise ReleaseValidationError(f"duplicate release path: {path}")
        paths.add(path)
        if item.get("object_type") != "tree":
            raise ReleaseValidationError(f"component {name} must bind a Git tree")
        _validate_sha(item.get("git_object_sha"), f"{name}.git_object_sha")
        _validate_sha(item.get("source_head"), f"{name}.source_head")
        if item.get("claim_status") not in ALLOWED_STATUS:
            raise ReleaseValidationError(f"unsupported claim status for {name}")
        boundary = item.get("claim_boundary")
        if not isinstance(boundary, str) or len(boundary.strip()) < 30:
            raise ReleaseValidationError(f"claim boundary missing for {name}")

    for section in ("formal_objects", "documentation_objects"):
        objects = data.get(section)
        if not isinstance(objects, list) or not objects:
            raise ReleaseValidationError(f"{section} must be non-empty")
        for item in objects:
            if not isinstance(item, dict):
                raise ReleaseValidationError(f"invalid entry in {section}")
            path = item.get("path")
            if not isinstance(path, str) or not path or path.startswith("/"):
                raise ReleaseValidationError(f"invalid path in {section}")
            if path in paths:
                raise ReleaseValidationError(f"duplicate release path: {path}")
            paths.add(path)
            if item.get("object_type") not in {"tree", "blob"}:
                raise ReleaseValidationError(f"invalid object type for {path}")
            _validate_sha(item.get("git_object_sha"), f"{path}.git_object_sha")

    lowered_paths = {path.lower() for path in paths}
    if any(path.startswith(".github/") for path in lowered_paths):
        raise ReleaseValidationError("release must not add workflow paths")
    if any(path.startswith(PROHIBITED_PREFIXES) for path in lowered_paths):
        raise ReleaseValidationError("experimental or domain-specific scope leaked into RC")

    promotion = data.get("promotion_gate")
    if not isinstance(promotion, str) or "before/after external delta" not in promotion:
        raise ReleaseValidationError("external-power promotion gate missing")


def _validate_bound_object(item: dict[str, Any], root: Path) -> None:
    relative = item["path"]
    path = root / relative
    if not path.exists() and not path.is_symlink():
        raise ReleaseValidationError(f"missing release object: {relative}")
    expected = item["git_object_sha"]
    if item["object_type"] == "blob":
        if not path.is_file() and not path.is_symlink():
            raise ReleaseValidationError(f"expected blob at {relative}")
        actual = git_blob_sha(path)
    else:
        actual = git_tree_sha(path)
    if actual != expected:
        raise ReleaseValidationError(
            f"Git {item['object_type']} mismatch for {relative}: {actual} != {expected}"
        )


def validate_checkout(data: dict[str, Any], root: Path) -> None:
    for component in data["components"]:
        _validate_bound_object(component, root)
    for section in ("formal_objects", "documentation_objects"):
        for item in data[section]:
            _validate_bound_object(item, root)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--root", type=Path)
    parser.add_argument("--manifest-only", action="store_true")
    args = parser.parse_args()

    data = json.loads(args.manifest.read_text(encoding="utf-8"))
    validate_manifest_data(data)
    if not args.manifest_only:
        root = args.root or args.manifest.parent
        validate_checkout(data, root.resolve())
    print("LOGIC_POWER_RELEASE_MANIFEST_PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, json.JSONDecodeError, ReleaseValidationError) as exc:
        print(f"LOGIC_POWER_RELEASE_MANIFEST_REJECTED: {exc}", file=sys.stderr)
        raise SystemExit(2)
