import unittest

from orchestrator.reasoning import resolve_reasoning


class ReasoningTests(unittest.TestCase):
    def test_explicit_modes_win(self):
        self.assertTrue(resolve_reasoning("on", ["code-explainer"], "解释"))
        self.assertFalse(resolve_reasoning("off", ["python-bugfix"], "修复"))

    def test_bugfix_skill_enables_auto(self):
        self.assertTrue(resolve_reasoning("auto", ["python-bugfix"], "handle it"))

    def test_explainer_skill_disables_auto(self):
        self.assertFalse(resolve_reasoning("auto", ["code-explainer"], "复杂解释"))

    def test_bugfix_language_enables_auto(self):
        self.assertTrue(resolve_reasoning("auto", [], "修复测试失败"))

    def test_simple_task_disables_auto(self):
        self.assertFalse(resolve_reasoning("auto", [], "列出文件"))


if __name__ == "__main__":
    unittest.main()
