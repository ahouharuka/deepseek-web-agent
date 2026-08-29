import unittest

from calculator import divide_total


class CalculatorTests(unittest.TestCase):
    def test_divides_total_equally(self):
        self.assertEqual(divide_total(100, 4), 25)


if __name__ == "__main__":
    unittest.main()
