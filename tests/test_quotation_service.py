import copy
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from quotation_service import generate_quotation

class TestQuotationService(unittest.TestCase):

    def setUp(self):
        self.text = (
            "Please quote 120 m2 of Standard Aluminium Cladding "
            "and 120 m2 of 50mm Insulation Board."
        )

        self.enquiry = {
            "source_text" : self.text,
            "items": [
                {
                    "description": "Standard Aluminium Cladding",
                    "quantity": 120.0,
                    "unit" : "m2",
                },
                {
                    "description": "50mm Insulation Board",
                    "quantity": 120.0,
                    "unit": "m2",
                },
            ],
        }

    def test_valid_quotation(self):
        matched, quotation = generate_quotation(
            self.enquiry, self.text
        )

        self.assertEqual(len(matched),2)
        self.assertAlmostEqual(quotation["total"], 22915.20)

    def test_changed_enquiry_rejected(self):
        with self.assertRaisesRegex(ValueError, "changed"):
            generate_quotation(
                self.enquiry,
                "A different customer enquiry",
            )

    def test_unknown_product_blocked(self):
        enquiry = copy.deepcopy(self.enquiry)
        enquiry["items"][0]["description"] = "Timber Cladding"

        with self.assertRaisesRegex(ValueError, "BLOCK"):
            generate_quotation(enquiry, self.text)

    def test_approximate_quantity_held(self):
        enquiry = copy.deepcopy(self.enquiry)

        # Explicitly use an approximate quantity
        enquiry["source_text"] = (
            "Please quote approximately 120 m2 of "
            "Standard Aluminium Cladding and"
            "120 m2 of 50mm Insulation Board."
        )

        with self.assertRaisesRegex(ValueError, "HOLD"):
            generate_quotation(
                enquiry,
                enquiry["source_text"]
            )

if __name__ == "__main__":
    unittest.main()
