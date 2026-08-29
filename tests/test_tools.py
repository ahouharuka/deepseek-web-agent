import tempfile
import unittest
from pathlib import Path

from tools.readonly import list_files, read_file, resolve_in_workspace, search_text


class ReadonlyToolTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.tempdir.name).resolve()
        (self.workspace / "hello.txt").write_text("alpha\nbeta\n", encoding="utf-8")

    def tearDown(self):
        self.tempdir.cleanup()

    def test_path_escape_is_rejected(self):
        with self.assertRaises(ValueError):
            resolve_in_workspace(self.workspace, "../outside.txt")

    def test_list_and_read(self):
        self.assertEqual(list_files(self.workspace, {"path": "."})[0]["path"], "hello.txt")
        self.assertEqual(read_file(self.workspace, {"path": "hello.txt"})["text"], "alpha\nbeta\n")

    def test_search(self):
        results = search_text(self.workspace, {"path": ".", "query": "BETA"})
        self.assertEqual(results[0]["line"], 2)

    def test_missing_path_suggests_close_existing_name(self):
        (self.workspace / "__init__.py").write_text("", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "__init__\\.py"):
            read_file(self.workspace, {"path": "init.py"})

    def test_sensitive_paths_are_hidden_and_denied(self):
        (self.workspace / ".env").write_text("TOKEN=value", encoding="utf-8")
        names = {item["path"] for item in list_files(self.workspace, {"path": "."})}
        self.assertNotIn(".env", names)
        with self.assertRaisesRegex(ValueError, "安全策略拒绝"):
            read_file(self.workspace, {"path": ".env"})

    def test_private_key_content_is_denied(self):
        (self.workspace / "config.txt").write_text(
            "-----BEGIN PRIVATE KEY-----\nnot-a-real-key\n", encoding="utf-8"
        )
        with self.assertRaisesRegex(ValueError, "疑似包含密钥"):
            read_file(self.workspace, {"path": "config.txt"})


if __name__ == "__main__":
    unittest.main()
