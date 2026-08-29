import tempfile
import unittest
from pathlib import Path

from orchestrator.skills import SkillCatalog, SkillError, apply_skills_to_task, parse_skill


class SkillTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.builtins = self.root / "builtins"
        self.workspace = self.root / "workspace"
        self.builtins.mkdir()
        self.workspace.mkdir()
        (self.builtins / "example.md").write_text(
            "---\nname: example\ndescription: Example workflow\n---\nRead files first.\n",
            encoding="utf-8",
        )

    def tearDown(self):
        self.tempdir.cleanup()

    def test_catalog_loads_explicit_skill(self):
        skill = SkillCatalog(self.builtins, self.workspace).load(["example"])[0]
        self.assertEqual(skill.name, "example")

    def test_unknown_skill_is_rejected(self):
        with self.assertRaises(SkillError):
            SkillCatalog(self.builtins, self.workspace).load(["missing"])

    def test_filename_must_match_name(self):
        path = self.builtins / "wrong.md"
        path.write_text("---\nname: other\ndescription: x\n---\nbody\n", encoding="utf-8")
        with self.assertRaises(SkillError):
            parse_skill(path)

    def test_skill_is_marked_as_non_permission_granting(self):
        skill = SkillCatalog(self.builtins, self.workspace).load(["example"])[0]
        combined = apply_skills_to_task("Fix it", [skill])
        self.assertIn("不授予额外工具", combined)
        self.assertIn("Read files first", combined)

    def test_duplicate_selection_is_rejected(self):
        with self.assertRaises(SkillError):
            SkillCatalog(self.builtins, self.workspace).load(["example", "example"])

    def test_builtin_explainer_requires_retry_after_read_failure(self):
        builtin_dir = Path(__file__).resolve().parents[1] / "agent_skills"
        skill = SkillCatalog(builtin_dir, self.workspace).load(["code-explainer"])[0]
        self.assertIn("纠正后重试", skill.instructions)
        self.assertIn("不得把“读取失败”解释成文件为空", skill.instructions)


if __name__ == "__main__":
    unittest.main()
