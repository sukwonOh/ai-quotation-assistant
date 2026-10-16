import json
import math
import re
from pathlib import Path

from gemini_extractor import extract_enquiry_gemini

# 1. Project paths

PROJECT_ROOT = Path(__file__).resolve().parents[1]

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "test"
    / "gemini_evaluation_report.json"
)

# 2. Synthetic test cases

TEST_CASES = [
    {
        "id": "standard",
        "text": (
            "Hi, I'm Alex from ABC Construction. "
            "Our project is in Parramatta, Sydney. "
            "Please quote 120 m2 of Standard Aluminium "
            "Cladding and 120 m2 of 50mm Insulation Board. "
            "Please include installation."
        ),
        "expected_name": "Alex",
        "expected_location": "Parramatta",
        "expected_items": [
            {
                "description": "Standard Aluminium Cladding",
                "quantity": 120.0
            },
            {
                "description": "50mm Insulation Board",
                "quantity": 120.0
            }
        ]
    },
    {
        "id": "informal",
        "text": (
            "Hey mate, I'm Sam. We're doing a job in Ryde. "
            "Could you price up about 80 square metres "
            "of Standard Aluminium Cladding? Cheers."
        ),
        "expected_name": "Sam",
        "expected_location": "Ryde",
        "expected_items": [
            {
                "description": "Standard Aluminium Cladding",
                "quantity": 80.0
            }
        ]
    },
    {
        "id": "missing_quantity",
        "text": (
            "Hi, I'm Maya. Can you quote 50mm Insulation "
            "Board for our project in Chatswood? "
            "I haven't measured the area yet."
        ),
        "expected_name": "Maya",
        "expected_location": "Chatswood",
        "expected_items": [
            {
                "description": "50mm Insulation Board",
                "quantity": None
            }
        ]
    }
]

# 3. Normalise text for comparison

def normalise(value):
    return " ".join(
        re.findall(
            r"[a-z0-9]+",
            str(value or "").lower()
        )
    )

# 4. Evaluate Gemini's extraction

def evaluate_case(case,extracted):

    errors = []

    customer = extracted.get("customer") or {}
    project = extracted.get("project") or {}
    items = extracted.get("items") or []

    # Check customer name
    if normalise(customer.get("name")) != normalise(
        case["expected_name"]
    ):
        errors.append("Incorrect customer name")

    # Check project location
    if normalise(case["expected_location"]) not in normalise(
        project.get("address")
    ):
        errors.append("Incorrect project location")

    # Check number of products
    if len(items) != len(case["expected_items"]):
        errors.append("Incorrect number of products")

    # Check product descriptions and quantities
    for expected in case["expected_items"]:

        matched = next(
            (
                item for item in items
                if normalise(item.get("description"))
                == normalise(expected["description"])
            ),
            None
        )

        if matched is None:
            errors.append(
                f"Product not found: {expected['description']}"
            )
            continue

        actual_qty = matched.get("quantity")
        expected_qty = expected["quantity"]

        if expected_qty is None:
            if actual_qty is not None:
                errors.append(
                    f"Expected missing quantity: "
                    f"{expected['description']}"
                )
        elif (
            not isinstance(actual_qty, (int, float))
            or not math.isfinite(actual_qty)
            or not math.isclose(
                actual_qty, expected_qty
            )
        ):
            errors.append(
                f"Incorrect quantity: "
                f"{expected['description']}"
            )

        if expected_qty is not None:
            if matched.get("unit") not in ("m2", "m²"):
                errors.append(
                    f"Incorrect unit: "
                    f"{expected['description']}"
                )

    # Preserve installation requirements
    if case["id"] == "standard":
        if "install" not in normalise(
            extracted.get("notes")
        ):
            errors.append(
                "Installation request missing from notes"
            )

    # Identify risks requiring review
    approximate = bool(
        re.search(
            r"\b(about|roughly|around|approximately)\b",
            case["text"].lower()
        )
    )

    missing_quantity = any(
        item.get("quantity") is None
        for item in items
    )

    hold_quotation = (
        approximate
        or missing_quantity
        or bool(errors)
    )

    return {
        "passed": len(errors) == 0,
        "errors": errors,
        "hold_quotation": hold_quotation,
        "approximate_quantity": approximate,
        "missing_quantity": missing_quantity
    }

# 5. Run all evaluations

def run_evaluation():

    results = []

    for case in TEST_CASES:
        print(f"\nTesting: {case['id']}")
        print("-" * 40)

        try:
            extracted = extract_enquiry_gemini(
                case["text"]
            )

            evaluation = evaluate_case(
                case, extracted
            )

            results.append({
                "test_id": case["id"],
                "evaluation": evaluation,
                "extracted": extracted
            })

            status = (
                "PASS" if evaluation["passed"]
                else "FAIL"
            )

            print(f"Result: {status}")

            if evaluation["hold_quotation"]:
                print("Quotation: HOLD FOR REVIEW")
            else:
                print("Quotation: DATA CHECKS PASSED")

            for error in evaluation["errors"]:
                print(f"  Issue: {error}")

        except Exception as error:

            print(f"ERROR: {error}")

            results.append({
                "test_id": case["id"],
                "evaluation": {
                    "passed": False,
                    "errors": [str(error)],
                    "hold_quotation": True
                }
            })

    # Calculate overall results

    passed = sum(
        result["evaluation"]["passed"]
        for result in results
    )

    report = {
        "total_tests": len(TEST_CASES),
        "passed_tests": passed,
        "failed_tests": len(TEST_CASES) - passed,
        "results": results
    }

    OUTPUT_FILE.parent.mkdir(
        parents=True, exist_ok=True
    )

    OUTPUT_FILE.write_text(
        json.dumps(
            report,
            indent=4,
            ensure_ascii=False
        ),
        encoding = "utf-8"
    )

    print("\nEVALUATION SUMMARY")
    print("=" * 40)
    print(f"Passed: {passed}/{len(TEST_CASES)}")
    print(f"Failed: {len(TEST_CASES) - passed}")
    print(f"Report saved to: {OUTPUT_FILE}")

if __name__ == "__main__":
    run_evaluation()
