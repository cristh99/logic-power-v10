from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "release_validator", ROOT / "tools" / "validate_logic_power_release.py"
)
assert SPEC and SPEC.loader
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)


class ReleaseManifestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = json.loads(
            (ROOT / "LOGIC_POWER_RELEASE_MANIFEST.json").read_text(encoding="utf-8")
        )

    def test_manifest_contract_passes(self) -> None:
        validator.validate_manifest_data(self.data)

    def test_global_score_laundering_is_rejected(self) -> None:
        forged = copy.deepcopy(self.data)
        forged["components"][0]["claim_status"] = "GLOBAL_1000"
        with self.assertRaises(validator.ReleaseValidationError):
            validator.validate_manifest_data(forged)

    def test_paid_or_interfering_release_is_rejected(self) -> None:
        for field, value in (
            ("paid_spend_usd", 1),
            ("active_agent_messages", 1),
            ("workflow_files_added", 1),
        ):
            forged = copy.deepcopy(self.data)
            forged["constraints"][field] = value
            with self.assertRaises(validator.ReleaseValidationError):
                validator.validate_manifest_data(forged)

    def test_experimental_scope_is_rejected(self) -> None:
        forged = copy.deepcopy(self.data)
        forged["documentation_objects"].append(
            {
                "path": "tree_power_outcomes_v1",
                "object_type": "tree",
                "git_object_sha": "0" * 40,
            }
        )
        with self.assertRaises(validator.ReleaseValidationError):
            validator.validate_manifest_data(forged)

    def test_source_drift_is_rejected(self) -> None:
        forged = copy.deepcopy(self.data)
        forged["components"][1]["source_head"] = "not-a-sha"
        with self.assertRaises(validator.ReleaseValidationError):
            validator.validate_manifest_data(forged)

    def test_tree_hash_matches_git_and_changes_on_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            root = repo / "content"
            (root / "sub").mkdir(parents=True)
            (root / "alpha.txt").write_text("alpha\n", encoding="utf-8")
            executable = root / "sub" / "run.sh"
            executable.write_text("#!/bin/sh\necho ok\n", encoding="utf-8")
            executable.chmod(0o755)

            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            subprocess.run(["git", "add", "content"], cwd=repo, check=True)
            top_tree = subprocess.check_output(
                ["git", "write-tree"], cwd=repo, text=True
            ).strip()
            expected = subprocess.check_output(
                ["git", "rev-parse", f"{top_tree}:content"], cwd=repo, text=True
            ).strip()
            self.assertEqual(validator.git_tree_sha(root), expected)

            before = validator.git_tree_sha(root)
            (root / "alpha.txt").write_text("mutated\n", encoding="utf-8")
            self.assertNotEqual(validator.git_tree_sha(root), before)

    def test_checkout_rejects_component_tree_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            components = []
            for name in sorted(validator.REQUIRED_COMPONENTS):
                path = root / name
                path.mkdir()
                (path / "core.py").write_text(f"NAME = {name!r}\n", encoding="utf-8")
                components.append(
                    {
                        "name": name,
                        "path": name,
                        "object_type": "tree",
                        "git_object_sha": validator.git_tree_sha(path),
                    }
                )
            formal = root / "formal"
            formal.mkdir()
            (formal / "model.tla").write_text("---- MODULE X ----\n", encoding="utf-8")
            doc = root / "README.md"
            doc.write_text("scope\n", encoding="utf-8")
            data = {
                "components": components,
                "formal_objects": [
                    {
                        "path": "formal",
                        "object_type": "tree",
                        "git_object_sha": validator.git_tree_sha(formal),
                    }
                ],
                "documentation_objects": [
                    {
                        "path": "README.md",
                        "object_type": "blob",
                        "git_object_sha": validator.git_blob_sha(doc),
                    }
                ],
            }
            validator.validate_checkout(data, root)
            (root / "logic_power_v10" / "core.py").write_text(
                "NAME = 'forged'\n", encoding="utf-8"
            )
            with self.assertRaises(validator.ReleaseValidationError):
                validator.validate_checkout(data, root)


if __name__ == "__main__":
    unittest.main()
