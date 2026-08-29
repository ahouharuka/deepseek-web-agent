import tempfile
import unittest
from pathlib import Path

from tools.runner import (
    _sanitized_environment,
    preview_run_python_file,
    preview_run_tests,
    run_python_file,
    run_tests,
)


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.tempdir.name).resolve()
        tests = self.workspace / "tests"
        tests.mkdir()
        (tests / "test_ok.py").write_text(
            "import unittest\n\nclass T(unittest.TestCase):\n    def test_ok(self):\n        self.assertEqual(2 + 2, 4)\n",
            encoding="utf-8",
        )

    def tearDown(self):
        self.tempdir.cleanup()

    def test_unittest_runner(self):
        result = run_tests(self.workspace, {"runner": "python_unittest", "path": "tests"})
        self.assertTrue(result["passed"])
        self.assertEqual(result["exit_code"], 0)

    def test_unknown_runner_is_rejected(self):
        with self.assertRaises(ValueError):
            run_tests(self.workspace, {"runner": "shell", "path": "tests"})

    def test_preview_contains_no_user_command(self):
        preview = preview_run_tests(self.workspace, {"runner": "python_unittest", "path": "tests"})
        self.assertIn("-m unittest discover", preview)

    def test_environment_does_not_inherit_credentials(self):
        environment = _sanitized_environment()
        self.assertNotIn("AWS_SECRET_ACCESS_KEY", environment)
        self.assertNotIn("GITHUB_TOKEN", environment)
        self.assertEqual(environment["PYTHONNOUSERSITE"], "1")

    def test_run_python_file(self):
        script = self.workspace / "hello.py"
        script.write_text("print('hello')\n", encoding="utf-8")
        result = run_python_file(self.workspace, {"path": "hello.py"})
        self.assertTrue(result["passed"])
        self.assertEqual(result["stdout"].strip(), "hello")
        self.assertIn("-I", preview_run_python_file(self.workspace, {"path": "hello.py"}))

    def test_run_python_file_rejects_non_python(self):
        (self.workspace / "notes.txt").write_text("hello", encoding="utf-8")
        with self.assertRaises(ValueError):
            run_python_file(self.workspace, {"path": "notes.txt"})
