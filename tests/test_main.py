import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from main import _run_session
from orchestrator.policy import Policy
from tools.registry import build_readonly_registry


class ImmediateModel:
    def __init__(self):
        self.tasks = []

    def start(self, task, tool_descriptions):
        self.tasks.append(task)
        return {"type": "final", "content": "done"}

    def continue_with_result(self, result):
        raise AssertionError("no continuation expected")


class InteractiveSessionTests(unittest.TestCase):
    def test_multiple_tasks_share_one_model_session(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            model = ImmediateModel()
            with patch("builtins.input", side_effect=["second task", "/exit"]):
                _run_session(
                    model,
                    build_readonly_registry(workspace),
                    Policy(workspace, auto_approve_readonly=True),
                    None,
                    "first task",
                    [],
                    10,
                    True,
                )
            self.assertEqual(model.tasks, ["first task", "second task"])


if __name__ == "__main__":
    unittest.main()
