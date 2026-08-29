import tempfile
import unittest
from pathlib import Path

from orchestrator.loop import AgentLoop
from orchestrator.policy import Policy
from tools.registry import build_readonly_registry


class RepairingModel:
    def start(self, task, tool_descriptions):
        return {"type": "read_file", "path": "x"}

    def continue_with_result(self, result):
        self.result = result
        return {"type": "final", "content": "recovered"}


class LoopTests(unittest.TestCase):
    def test_protocol_error_is_returned_for_repair(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            model = RepairingModel()
            loop = AgentLoop(
                model,
                build_readonly_registry(workspace),
                Policy(workspace, auto_approve_readonly=True),
            )
            self.assertEqual(loop.run("test"), "recovered")
            self.assertEqual(model.result["type"], "protocol_error")


if __name__ == "__main__":
    unittest.main()
