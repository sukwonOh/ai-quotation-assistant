import json
import math
import re
from pathlib import Path

from gemini_extractor import extract_enquiry_gemini
from quotation_safety import check_quotation_safety

# 1. Project paths

PROJECT_ROOT = Path(__file__).resolve().parents[1]

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "test"
    / "gemini_evaluation_report.json"
)

BENCHMARK_FILE = (
    PROJECT_ROOT
    / "data"
    / "evaluation"
    / "benchmark_cases.json"
)

CATALOGUE_FILE = (
    PROJECT_ROOT
    / "data"
    / "synthetic"
    / "product_catalogue.csv"
)
# 2. Synthetic test cases

TEST_CASES = [
    {
        "id": "standard",
        "expected_safety_status": "DRAFT",
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
        "expected_safety_status": "HOLD",
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
        "expected_safety_status": "BLOCK",
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

# Load original and additional benchmark cases
def load_all_test_cases():

    new_cases = json.loads(
        BENCHMARK_FILE.read_text(encoding="utf-8")
    )

    if not isinstance(new_cases, list):
        raise ValueError(
            "Benchmark dataset must be a JSON list."
        )

    all_cases = TEST_CASES + new_cases

    # Prevent duplicated test case IDs
    case_ids = [case["id"] for case in all_cases]

    if len(case_ids) != len(set(case_ids)):
        raise ValueError(
            "Duplicate benchmark case IDs detected."
        )

    return all_cases

# 3. Normalise text for comparison

def normalise(value):
    return " ".join(
        re.findall(
            r"[a-z0-9]+",
            str(value or "").lower()
        )
    )

def evaluate_fields(case, extracted):
    """Measure extraction accuracy separately for each field."""

    field_names = (
        "customer_name",
        "project_location",
        "product_count",
        "product_description",
        "quantity",
        "unit",
    )

    results = {
        field: {"correct": 0, "total": 0}
        for field in field_names
    }

    def score(field, correct):
        results[field]["total"] += 1
        results[field]["correct"] += int(bool(correct))

    def normalise_unit(unit):
        return (
            str(unit or "")
            .strip()
            .lower()
            .replace("²", "2")
            .replace(" ", "")
        )

    customer = extracted.get("customer") or {}
    project = extracted.get("project") or {}
    items = extracted.get("items") or []

    score(
        "customer_name",
        normalise(customer.get("name"))
        == normalise(case["expected_name"]),
    )

    expected_location = normalise(case["expected_location"])
    actual_location = normalise(project.get("address"))

    score(
        "project_location",
        bool(expected_location)
        and expected_location in actual_location,
    )

    expected_items = case["expected_items"]

    score("product_count", len(items) == len(expected_items))

    # Match each predicted product at most once.
    remaining_items = list(items)

    for expected in expected_items:
        expected_description = normalise(
            expected["description"]
        )

        match_index = next(
            (
                i for i, item in enumerate(remaining_items)
                if normalise(item.get("description"))
                == expected_description
            ),
            None,
        )

        matched = (
            remaining_items.pop(match_index)
            if match_index is not None
            else None
        )

        score("product_description", matched is not None)

        expected_qty = expected["quantity"]
        actual_qty = (
            matched.get("quantity")
            if matched is not None
            else None
        )

        if matched is None:
            quantity_correct = False
        elif expected_qty is None:
            quantity_correct = actual_qty is None
        else:
            quantity_correct = (
                isinstance(actual_qty, (int, float))
                and not isinstance(actual_qty, bool)
                and math.isfinite(actual_qty)
                and math.isclose(actual_qty, expected_qty)
            )

        score("quantity", quantity_correct)

        # Missing-quantity cases have no expected unit.
        if expected_qty is not None:
            expected_unit = expected.get("unit", "m2")
            actual_unit = (
                matched.get("unit")
                if matched is not None
                else None
            )

            score(
                "unit",
                matched is not None
                and normalise_unit(actual_unit)
                == normalise_unit(expected_unit),
            )

    for stats in results.values():
        total = stats["total"]
        stats["accuracy_percent"] = (
            round(100 * stats["correct"] / total, 2)
            if total
            else None
        )

    return results

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

# Evaluate actual quotation safety classification
def evaluate_safety_case(case, extracted):

    expected_status = case["expected_safety_status"]

    # Ensure the validator checks original customer wording
    enquiry = {
        **extracted,
        "source_text": case["text"],
    }

    safety = check_quotation_safety(
        enquiry,
        CATALOGUE_FILE
    )

    actual_status = safety["status"]

    return {
        "passed": actual_status == expected_status,
        "expected_status": expected_status,
        "actual_status": actual_status,
        "errors": safety["errors"],
        "warnings": safety["warnings"],
    }

def aggregate_field_accuracy(results):
    """Aggregate field-level results across evaluated cases."""

    field_names = (
        "customer_name",
        "project_location",
        "product_count",
        "product_description",
        "quantity",
        "unit",
    )

    summary = {
        field: {"correct": 0, "total": 0}
        for field in field_names
    }

    evaluated_cases = 0

    for result in results:
        fields = result.get("field_evaluation")

        if fields is None:
            continue

        evaluated_cases += 1

        for field in field_names:
            summary[field]["correct"] += fields[field]["correct"]
            summary[field]["total"] += fields[field]["total"]

    for stats in summary.values():
        total = stats["total"]

        stats["accuracy_percent"] = (
            round(100 * stats["correct"] / total, 2)
            if total > 0
            else None
        )

    return {
        "total_cases": len(results),
        "evaluated_cases": evaluated_cases,
        "metrics": summary,
    }

def run_evaluation():

    results = []
    all_cases = load_all_test_cases()

    for case in all_cases:
        print(f"\nTesting: {case['id']}")
        print("-" * 40)

        try:
            extracted = extract_enquiry_gemini(
                case["text"]
            )

            evaluation = evaluate_case(
                case, extracted
            )

            field_evaluation = evaluate_fields(
                case, extracted
            )

            # Evaluate actual safety classification
            safety_evaluation = evaluate_safety_case(
            case, extracted
            )

            results.append({
                "test_id": case["id"],
                "evaluation": evaluation,
                "field_evaluation": field_evaluation,
                "safety_evaluation": safety_evaluation,
                "extracted": extracted
            })

            status = (
                "PASS" if evaluation["passed"]
                else "FAIL"
            )

            print(f"Extraction result: {status}")

            # Display actual safety classification
            actual_safety = safety_evaluation["actual_status"]
            expected_safety = safety_evaluation["expected_status"]

            safety_result = (
                "PASS" if safety_evaluation["passed"]
                else "FAIL"
            )

            print(f"Safety classification: {actual_safety}")
            print(f"Expected safety: {expected_safety}")
            print(f"Safety evaluation: {safety_result}")

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
    field_accuracy_summary = aggregate_field_accuracy(results)

    passed = sum(
        result["evaluation"]["passed"]
        for result in results
    )

    # Overall extraction pass rate
    total_cases = len(all_cases)

    extraction_accuracy = round(
        (passed / total_cases) * 100, 2
    )

    # Safety accuracy for successfully evaluated cases
    safety_results = [
        result["safety_evaluation"]
        for result in results
        if "safety_evaluation" in result
    ]

    safety_evaluated = len(safety_results)

    safety_passed = sum(
        result["passed"]
        for result in safety_results
    )

    safety_accuracy = (
        round((safety_passed / safety_evaluated) * 100, 2)
        if safety_evaluated
        else None
    )



    report = {
        "total_tests": len(all_cases),
        "passed_tests": passed,
        "failed_tests": len(all_cases) - passed,
        "extraction_accuracy_percent": extraction_accuracy,
        "safety_evaluated": safety_evaluated,
        "safety_passed": safety_passed,
        "safety_accuracy_percent": safety_accuracy,
        "field_accuracy_summary": field_accuracy_summary,
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
    print(f"Passed: {passed}/{len(all_cases)}")
    print(f"Failed: {len(all_cases) - passed}")
    print(f"Report saved to: {OUTPUT_FILE}")
    print(f"Extraction pass rate: {extraction_accuracy}%")

    if safety_accuracy is not None:
        print(
            f"Safety accuracy: {safety_accuracy}% "
            f"({safety_passed}/{safety_evaluated} evaluated)"
        )
    else:
        print("Safety accuracy: Not available")

    print("\nFIELD-LEVEL ACCURACY")
    print("=" * 40)

    print(
        f"Evaluated cases: "
        f"{field_accuracy_summary['evaluated_cases']}/"
        f"{field_accuracy_summary['total_cases']}"
    )

    for field, stats in field_accuracy_summary["metrics"].items():
        accuracy = stats["accuracy_percent"]

        accuracy_text = (
            f"{accuracy:.2f}%"
            if accuracy is not None
            else "N/A"
        )

        print(
            f"{field}: {accuracy_text} "
            f"({stats['correct']}/{stats['total']})"
        )

if __name__ == "__main__":
    run_evaluation()
