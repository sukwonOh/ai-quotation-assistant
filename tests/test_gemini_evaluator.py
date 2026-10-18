import copy
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from gemini_evaluator import (
    TEST_CASES,
    evaluate_case,
    evaluate_fields,
    aggregate_field_accuracy,
    load_all_test_cases,
    evaluate_safety_case,
)

class TestGeminiEvaluator(unittest.TestCase):

    def setUp(self):
        self.cases = {
            case["id"]: case for case in TEST_CASES
        }

        self.standard_output = {
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
            "notes": "Please include installation.",
        }

    def test_correct_extraction_passes(self):
        result = evaluate_case(
            self.cases["standard"],
            self.standard_output
        )

        self.assertTrue(result["passed"])
        self.assertEqual(result["errors"], [])

    def test_incorrect_quantity_fails(self):
        extracted = copy.deepcopy(self.standard_output)
        extracted["items"][0]["quantity"] = 999

        result = evaluate_case(
            self.cases["standard"],
            extracted
        )

        self.assertFalse(result["passed"])

    def test_missing_product_fails(self):
        extracted = copy.deepcopy(self.standard_output)
        extracted["items"].pop()

        result = evaluate_case(
            self.cases["standard"],
            extracted
        )

        self.assertFalse(result["passed"])

    def test_incorrect_customer_fails(self):
        extracted = copy.deepcopy(self.standard_output)
        extracted["customer"]["name"] = "Unknown"

        result = evaluate_case(
            self.cases["standard"],
            extracted
        )

        self.assertFalse(result["passed"])

    def test_missing_installation_note_fails(self):
        extracted = copy.deepcopy(self.standard_output)
        extracted["notes"] = None

        result = evaluate_case(
            self.cases["standard"],
            extracted
        )

        self.assertFalse(result["passed"])

    def test_approximate_quantity_requires_review(self):
        extracted = {
            "customer": {"name": "Sam"},
            "project": {"address": "Ryde"},
            "items": [
                {
                    "description": "Standard Aluminium Cladding",
                    "quantity": 80.0,
                    "unit": "m2",
                }
            ],
            "notes": None,
        }

        result = evaluate_case(
            self.cases["informal"],
            extracted
        )

        self.assertTrue(result["passed"])
        self.assertTrue(result["hold_quotation"])
        self.assertTrue(result["approximate_quantity"])

    def test_missing_quantity_requires_review(self):
        extracted = {
            "customer": {"name": "Maya"},
            "project": {"address": "Chatswood"},
            "items": [
                {
                    "description": "50mm Insulation Board",
                    "quantity": None,
                    "unit": None,
                }
            ],
            "notes": "I haven't measured the area yet.",
        }

        result = evaluate_case(
            self.cases["missing_quantity"],
            extracted
        )

        self.assertTrue(result["passed"])
        self.assertTrue(result["hold_quotation"])
        self.assertTrue(result["missing_quantity"])

    def test_benchmark_safety_classifications(self):

        for case in load_all_test_cases():

            with self.subTest(case=case["id"]):

                # Construct ideal extraction from ground truth
                extracted = {
                    "items": [
                        {
                            "description": item["description"],
                            "quantity": item["quantity"],
                            "unit": (
                                "m2"
                                if item["quantity"] is not None
                                else None
                            ),
                        }
                        for item in case["expected_items"]
                    ],
                    "notes": None,
                }

                result = evaluate_safety_case(
                    case,
                    extracted
                )

                self.assertTrue(
                    result["passed"],
                    msg=f"{case['id']}: {result}"
                )

    def test_field_accuracy_all_correct(self):
        result = evaluate_fields(
            self.cases["standard"],
            self.standard_output,
        )

        for field, stats in result.items():
            self.assertEqual(
                stats["accuracy_percent"],
                100.0,
                msg=f"Incorrect score for {field}",
            )

    def test_field_accuracy_detects_errors(self):
        extracted = copy.deepcopy(self.standard_output)

        extracted["customer"]["name"] = "Wrong Name"
        extracted["items"][0]["quantity"] = 999

        result = evaluate_fields(
            self.cases["standard"],
            extracted,
        )

        self.assertEqual(
            result["customer_name"]["accuracy_percent"],
            0.0,
        )

        self.assertEqual(
            result["quantity"]["accuracy_percent"],
            50.0,
        )

        self.assertEqual(
            result["product_description"]["accuracy_percent"],
            100.0,
        )

    def test_aggregate_field_accuracy(self):
        case = self.cases["standard"]

        correct = evaluate_fields(
            case,
            self.standard_output,
        )

        incorrect_output = copy.deepcopy(
            self.standard_output
        )

        incorrect_output["customer"]["name"] = "Wrong Name"
        incorrect_output["items"][0]["quantity"] = 999

        incorrect = evaluate_fields(
            case,
            incorrect_output,
        )

        summary = aggregate_field_accuracy([
            {"field_evaluation": correct},
            {"field_evaluation": incorrect},
            {"test_id": "failed_api_call"},
        ])

        self.assertEqual(summary["total_cases"], 3)
        self.assertEqual(summary["evaluated_cases"], 2)

        metrics = summary["metrics"]

        self.assertEqual(
            metrics["customer_name"]["accuracy_percent"],
            50.0,
        )

        self.assertEqual(
            metrics["quantity"]["accuracy_percent"],
            75.0,
        )

        self.assertEqual(
            metrics["product_description"]["accuracy_percent"],
            100.0,
        )


if __name__ == "__main__":
    unittest.main()
