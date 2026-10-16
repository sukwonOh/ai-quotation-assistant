import copy
import json
import unittest
from pathlib import Path

from src.quotation_safety import check_quotation_safety

PROJECT_ROOT = Path(__file__).resolve().parents[1]

CATALOGUE_FILE = (
    PROJECT_ROOT / "data" / "synthetic"
    / "product_catalogue.csv"
)

SAMPLE_FILE = (
    PROJECT_ROOT / "data" / "test"
    / "gemini_enquiry_sample.json"
)

class TestQuotationSafety(unittest.TestCase):

    def setUp(self):
        self.enquiry = json.loads(
            SAMPLE_FILE.read_text(encoding="utf-8")
        )

    def check(self):
        return check_quotation_safety(
            self.enquiry,
            CATALOGUE_FILE
        )

    # 1. Valid enquiry
    def test_valid_enquiry(self):
        self.enquiry["source_text"] = ""
        self.enquiry["notes"] = ""

        result = self.check()

        self.assertEqual(result["status"], "DRAFT")
        self.assertEqual(result["errors"], [])

    # 2. Missing quantity
    def test_missing_quantity(self):
        self.enquiry["items"][0]["quantity"] = None

        result = self.check()

        self.assertEqual(result["status"], "BLOCK")

    # 3. Unknown product
    def test_unknown_product(self):
        self.enquiry["items"][0]["description"] = (
            "Unknown Solar Cladding"
        )

        result = self.check()

        self.assertEqual(result["status"], "BLOCK")

    # 4. Negative quantity
    def test_negative_quantity(self):
        self.enquiry["items"][0]["quantity"] = -50

        result = self.check()

        self.assertEqual(result["status"], "BLOCK")

    # 5. Approximate quantity
    def test_approximate_quantity(self):
        self.enquiry["source_text"] = (
            "Please quote about 120 m2 of "
            "Standard Aluminium Cladding."
        )

        result = self.check()

        self.assertEqual(result["status"], "HOLD")

    # 6. Installation review
    def test_installation_review(self):
        result = self.check()

        self.assertEqual(result["status"], "DRAFT")
        self.assertTrue(result["review_required"])
        self.assertTrue(
            any(
                "Installation" in warning
                for warning in result["warnings"]
            )
        )

if __name__ == "__main__":
    unittest.main()
