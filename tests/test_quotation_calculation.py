
import sys
import unittest
from pathlib import Path

# Project configuration
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from quotation_module import (
    create_quotation,
    create_full_quotation,
)


class TestQuotationCalculation(unittest.TestCase):

    def test_single_product_calculation(self):
        result = create_quotation("CLD001", 120)

        self.assertEqual(result["material_quantity"], 132.0)
        self.assertEqual(result["material_cost"], 11220.0)
        self.assertEqual(result["labour_cost"], 5400.0)
        self.assertEqual(result["subtotal"], 16620.0)
        self.assertEqual(result["gst"], 1662.0)
        self.assertEqual(result["total"], 18282.0)

    def test_multiple_product_calculation(self):
        items = [
            {"product_id": "CLD001", "quantity": 120},
            {"product_id": "INS001", "quantity": 120},
        ]

        result = create_full_quotation(items)

        self.assertEqual(len(result["items"]), 2)
        self.assertEqual(result["subtotal"], 20832.0)
        self.assertEqual(result["gst"], 2083.2)
        self.assertEqual(result["total"], 22915.2)

    def test_zero_quantity_rejected(self):
        with self.assertRaises(ValueError):
            create_quotation("CLD001", 0)

    def test_negative_quantity_rejected(self):
        with self.assertRaises(ValueError):
            create_quotation("CLD001", -50)

    def test_unknown_product_rejected(self):
        with self.assertRaises(ValueError):
            create_quotation("UNKNOWN001", 120)

    def test_non_finite_quantity_rejected(self):
        for quantity in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(quantity=quantity):
                with self.assertRaises(ValueError):
                    create_quotation("CLD001", quantity)

    def test_boolean_quantity_rejected(self):
        with self.assertRaises(ValueError):
            create_quotation("CLD001", True)

    def test_empty_quotation_rejected(self):
        with self.assertRaises(ValueError):
            create_full_quotation([])

if __name__ == "__main__":
    unittest.main()
