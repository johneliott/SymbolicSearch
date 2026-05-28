import unittest
from preprocessor import find_pure_literals

class TestPureLiteralElimination(unittest.TestCase):
    def test_find_pure_literals(self):
        # x1 is pure positive, x2 is mixed, x3 is pure negative, x4 is absent
        formula = [
            [1, 2, -3],
            [1, -2]
        ]
        pure_literals = find_pure_literals(formula)
        # Expected: 1, -3
        self.assertEqual(pure_literals, [1, -3])

    def test_no_pure_literals(self):
        # x1 and x2 are mixed
        formula = [
            [1, 2],
            [-1, -2]
        ]
        pure_literals = find_pure_literals(formula)
        self.assertEqual(pure_literals, [])

    def test_all_pure_literals(self):
        # x1, x2, x3 are pure
        formula = [
            [1, 2],
            [2, 3]
        ]
        pure_literals = find_pure_literals(formula)
        self.assertEqual(pure_literals, [1, 2, 3])

if __name__ == '__main__':
    unittest.main()
