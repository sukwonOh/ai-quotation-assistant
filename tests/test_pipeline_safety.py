import copy
import json
import sys
import tempfile
import unittest

from pathlib import Path
from unittest.mock import patch

# 1. Project configuration

PROJECT_ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(
    0, str(PROJECT_ROOT / "src")
)

import gemini_to_quotation as pipeline

SAMPLE_FILE = (
    PROJECT_ROOT
    / "tests"
    / "fixtures"
    / "enquiry_sample.json"
)

# 2. Pipeline safety tests

class TestPipelineSafety(unittest.TestCase):

    def setUp(self):
        self.enquiry = json.loads(
            SAMPLE_FILE.read_text(encoding="utf-8")
        )

    def verify_pipeline_stops(
            self, enquiry, expected_status
    ):
        # Create temporary test files.
        # Our original JSON remains unchanged.

        with tempfile.TemporaryDirectory() as folder:

            test_input = Path(folder) / "enquiry.json"
            test_output = Path(folder) / "quotation.json"

            test_input.write_text(
                json.dumps(enquiry),
                encoding="utf-8"
            )

            # Temporarily redirect the pipeline
            # to our synthetic test input.

            with(
                patch.object(
                    pipeline, "INPUT_FILE", test_input
                ),
                patch.object(
                    pipeline, "OUTPUT_FILE", test_output
                ),
                patch.object(
                    pipeline,
                    "create_full_quotation",
                    side_effect = AssertionError(
                        "Unsafe enquiry reached pricing engine"
                    )
                )
            ):
                with self.assertRaises(SystemExit) as error:
                    pipeline.create_quotation_from_gemini()

            self.assertIn(
                expected_status,
                str(error.exception)
            )

            # A blocked/held enquriy must not
            # produce a new quotation file.

            self.assertFalse(test_output.exists())

    # Test 1 : Missing quantity

    def test_missing_quantity_blocked(self):

        enquiry = copy.deepcopy(self.enquiry)

        enquiry["items"][0]["quantity"] = None

        self.verify_pipeline_stops(
            enquiry, "BLOCK"
        )

    # Test 2 : Unknown product

    def test_unknown_product_blocked(self):

        enquiry = copy.deepcopy(self.enquiry)

        enquiry["items"][0]["description"] = (
            "Unknown Solar Cladding"
        )

        self.verify_pipeline_stops(
            enquiry, "BLOCK"
        )

    # Test 3 : Negative quantity

    def test_negative_quantity_blocked(self):

        enquiry = copy.deepcopy(self.enquiry)

        enquiry["items"][0]["quantity"] = -50

        self.verify_pipeline_stops(
            enquiry, "BLOCK"
        )

    # Test 4 : Approximate quantity

    def test_approximate_quantity_held(self):

        enquiry = copy.deepcopy(self.enquiry)

        enquiry["source_text"] = (
            "Please quote about 120 m2 of"
            "Standard Aluminium Cladding"
            "and 120 m2 of 50mm Insulation Board"
        )

        self.verify_pipeline_stops(
            enquiry, "HOLD"
        )

if __name__ == "__main__":
    unittest.main()
