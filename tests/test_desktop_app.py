import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from desktop_app import app_data_dir, resource_root
from orchestrator.policy import Policy, PolicyDenied
from orchestrator.protocol import ToolCall


class DesktopSupportTests(unittest.TestCase):
    def test_resource_root_exists(self):
        self.assertTrue(resource_root().is_dir())

    def test_app_data_directory_is_created(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.dict("os.environ", {"LOCALAPPDATA": temp}):
                path = app_data_dir()
            self.assertEqual(path, Path(temp) / "DeepSeekWebAgent")
            self.assertTrue(path.is_dir())

    def test_macos_app_data_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch("desktop_app.sys.platform", "darwin"), patch(
                "desktop_app.Path.home", return_value=Path(temp)
            ):
                path = app_data_dir()
            self.assertEqual(
                path,
                Path(temp) / "Library" / "Application Support" / "DeepSeekWebAgent",
            )
            self.assertTrue(path.is_dir())

    def test_policy_uses_gui_approver(self):
        call = ToolCall("tool_call", "1", "create_text_file", {"path": "x.py"})
        policy = Policy(Path.cwd(), approver=lambda *args: True)
        policy.authorize(call, readonly=False, preview="diff", approval_label="创建文件")
        denied = Policy(Path.cwd(), approver=lambda *args: False)
        with self.assertRaises(PolicyDenied):
            denied.authorize(call, readonly=False, preview="diff", approval_label="创建文件")


if __name__ == "__main__":
    unittest.main()
