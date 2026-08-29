import tempfile
import unittest
from pathlib import Path

from tools.write import apply_text_patch, create_text_file, preview_text_patch, replace_line


class WriteToolTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.tempdir.name).resolve()
        (self.workspace / "sample.py").write_text("value = 1\n", encoding="utf-8")

    def tearDown(self):
        self.tempdir.cleanup()

    def test_preview_and_apply_exact_replacement(self):
        args = {"path": "sample.py", "old_text": "value = 1", "new_text": "value = 2"}
        self.assertIn("+value = 2", preview_text_patch(self.workspace, args))
        apply_text_patch(self.workspace, args)
        self.assertEqual((self.workspace / "sample.py").read_text(encoding="utf-8"), "value = 2\n")

    def test_ambiguous_replacement_is_rejected(self):
        (self.workspace / "sample.py").write_text("x\nx\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            apply_text_patch(self.workspace, {"path": "sample.py", "old_text": "x", "new_text": "y"})

    def test_noop_text_replacement_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "没有实际变化"):
            apply_text_patch(
                self.workspace,
                {"path": "sample.py", "old_text": "value = 1", "new_text": "value = 1"},
            )

    def test_escape_is_rejected(self):
        with self.assertRaises(ValueError):
            apply_text_patch(self.workspace, {"path": "../sample.py", "old_text": "x", "new_text": "y"})

    def test_create_refuses_overwrite(self):
        with self.assertRaises(ValueError):
            create_text_file(self.workspace, {"path": "sample.py", "content": "new"})

    def test_create_new_text_file(self):
        result = create_text_file(self.workspace, {"path": "new.md", "content": "hello\n"})
        self.assertTrue(result["created"])
        self.assertEqual((self.workspace / "new.md").read_text(encoding="utf-8"), "hello\n")

    def test_create_file_from_lines(self):
        result = create_text_file(
            self.workspace,
            {"path": "random_numbers.py", "lines": ["import random", "", "print([random.randint(1, 100) for _ in range(10)])"]},
        )
        self.assertTrue(result["created"])
        self.assertEqual(
            (self.workspace / "random_numbers.py").read_text(encoding="utf-8"),
            "import random\n\nprint([random.randint(1, 100) for _ in range(10)])\n",
        )

    def test_create_lines_reject_embedded_newlines(self):
        with self.assertRaises(ValueError):
            create_text_file(self.workspace, {"path": "bad.py", "lines": ["first\nsecond"]})

    def test_replace_line_requires_expected_content(self):
        with self.assertRaises(ValueError):
            replace_line(self.workspace, {"path": "sample.py", "line_number": 1, "expected": "wrong", "replacement": "value = 2"})

    def test_noop_line_replacement_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "没有实际变化"):
            replace_line(
                self.workspace,
                {"path": "sample.py", "line_number": 1, "expected": "value = 1", "replacement": "value = 1"},
            )

    def test_replace_line(self):
        result = replace_line(self.workspace, {"path": "sample.py", "line_number": 1, "expected": "value = 1", "replacement": "value = 2"})
        self.assertEqual(result["line_number"], 1)
        self.assertEqual((self.workspace / "sample.py").read_text(encoding="utf-8"), "value = 2\n")


if __name__ == "__main__":
    unittest.main()
