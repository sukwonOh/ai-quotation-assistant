
import copy
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from consistency_evaluator import evaluate_consistency


class TestConsistencyEvaluator(unittest.TestCase):

    def setUp(self):
        self.output = {
            "customer": {"name": "Alex"},
            "project": {"address": "Parramatta, Sydney"},
            "items": [
                {
                    "description": "Standard Aluminium Cladding",
                    "quantity": 120.0,
                    "unit": "m2",
                },
                {
                    "description": "50mm Insulation Board",
                    "quantity": 120.0,
                    "unit": "m2",
                },
            ],
        }

    def test_identical_outputs(self):
        results = evaluate_consistency([
            copy.deepcopy(self.output)
            for _ in range(3)
        ])

        self.assertEqual(results["agreement_percent"], 100.0)
        self.assertEqual(results["distinct_outputs"], 1)

    def test_product_order_does_not_matter(self):
        reordered = copy.deepcopy(self.output)
        reordered["items"].reverse()
        reordered["items"][0]["unit"] = "m²"

        results = evaluate_consistency([
            self.output,
            reordered,
        ])

        self.assertEqual(results["agreement_percent"], 100.0)

    def test_changed_quantity_reduces_consistency(self):
        incorrect = copy.deepcopy(self.output)
        incorrect["items"][0]["quantity"] = 150.0

        results = evaluate_consistency([
            self.output,
            copy.deepcopy(self.output),
            incorrect,
        ])

        self.assertEqual(results["agreement_percent"], 33.33)
        self.assertEqual(results["distinct_outputs"], 2)

    def test_requires_multiple_runs(self):
        with self.assertRaises(ValueError):
            evaluate_consistency([self.output])


if __name__ == "__main__":
    unittest.main()
