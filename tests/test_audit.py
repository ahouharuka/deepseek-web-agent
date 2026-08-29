import json
import tempfile
import unittest
from pathlib import Path

from orchestrator.audit import AuditLog


class AuditLogTests(unittest.TestCase):
    def test_sensitive_fields_and_secrets_are_redacted(self):
        with tempfile.TemporaryDirectory() as temp:
            audit = AuditLog(Path(temp))
            audit.write(
                "tool_result",
                {
                    "task": "private task",
                    "arguments": {"path": "safe.py", "new_text": "private source"},
                    "lines": ["private", "source"],
                    "message": "github" + "_pat_" + "abcdefghijklmnopqrstuvwxyz123456",
                },
            )
            record = json.loads(audit.path.read_text(encoding="utf-8"))
            self.assertEqual(record["data"]["task"]["redacted"], True)
            self.assertEqual(record["data"]["arguments"]["new_text"]["redacted"], True)
            self.assertEqual(record["data"]["message"], "[redacted: likely secret]")
            self.assertEqual(record["data"]["lines"], "[redacted]")


if __name__ == "__main__":
    unittest.main()
