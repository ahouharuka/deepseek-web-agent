import unittest

from orchestrator.protocol import ProtocolError, ToolCall, parse_agent_message


class ProtocolTests(unittest.TestCase):
    def test_valid_tool_call(self):
        message = parse_agent_message({"type": "tool_call", "id": "1", "tool": "read_file", "arguments": {"path": "a.txt"}})
        self.assertIsInstance(message, ToolCall)

    def test_extra_fields_are_rejected(self):
        with self.assertRaises(ProtocolError):
            parse_agent_message({"type": "final", "content": "done", "command": "danger"})

    def test_unknown_type_is_rejected(self):
        with self.assertRaises(ProtocolError):
            parse_agent_message({"type": "shell", "content": "whoami"})


if __name__ == "__main__":
    unittest.main()
