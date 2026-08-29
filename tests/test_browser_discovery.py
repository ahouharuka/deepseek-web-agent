import tempfile
import unittest
from pathlib import Path

from adapters.browser_discovery import find_browser_executable


class BrowserDiscoveryTests(unittest.TestCase):
    def test_explicit_existing_browser_wins(self):
        with tempfile.TemporaryDirectory() as temp:
            executable = Path(temp) / "browser"
            executable.write_text("", encoding="utf-8")
            self.assertEqual(find_browser_executable(executable), executable.resolve())

    def test_explicit_missing_browser_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ValueError):
                find_browser_executable(Path(temp) / "missing")


if __name__ == "__main__":
    unittest.main()
