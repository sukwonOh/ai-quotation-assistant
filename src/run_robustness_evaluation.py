
"""Evaluate Gemini on challenging construction enquiries."""

import json
import time
from datetime import datetime, timezone
from pathlib import Path

from gemini_extractor import extract_enquiry_gemini
from gemini_evaluator import (
    evaluate_case,
    evaluate_fields,
    evaluate_safety_case,
    aggregate_field_accuracy,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]

BENCHMARK_FILE = (
    PROJECT_ROOT / "data" / "evaluation" / "robustness_cases.json"
)

OUTPUT_FILE = (
    PROJECT_ROOT / "data" / "test" / "robustness_report.json"
)

DELAY_SECONDS = 10


def run_robustness_benchmark():
    """Run challenging enquiries through the extraction pipeline."""

    cases = json.loads(
        BENCHMARK_FILE.read_text(encoding="utf-8")
    )

    if not isinstance(cases, list) or not cases:
        raise ValueError("Robustness dataset must be a non-empty list.")

    results = []

    for index, case in enumerate(cases):
        case_id = case["id"]

        print(f"\nTesting: {case_id}")
        print("-" * 40)

        try:
            extracted = extract_enquiry_gemini(case["text"])

            extraction_evaluation = evaluate_case(
                case, extracted
            )

            field_evaluation = evaluate_fields(
                case, extracted
            )

            safety_evaluation = evaluate_safety_case(
                case, extracted
            )

            results.append({
                "test_id": case_id,
                "extraction_evaluation": extraction_evaluation,
                "field_evaluation": field_evaluation,
                "safety_evaluation": safety_evaluation,
                "extracted": extracted,
            })

            print(
                "Extraction: "
                + ("PASS" if extraction_evaluation["passed"] else "FAIL")
            )

            print(
                f"Safety: {safety_evaluation['actual_status']}"
                f" (expected {safety_evaluation['expected_status']})"
            )

            print(
                "Safety evaluation: "
                + ("PASS" if safety_evaluation["passed"] else "FAIL")
            )

        except Exception as error:
            print(f"API or evaluation error: {error}")

            results.append({
                "test_id": case_id,
                "error": str(error),
            })

            # Stop rather than repeatedly calling a failing API.
            break

        if index < len(cases) - 1:
            time.sleep(DELAY_SECONDS)

    successful = [
        result for result in results
        if "extraction_evaluation" in result
    ]

    extraction_passed = sum(
        result["extraction_evaluation"]["passed"]
        for result in successful
    )

    safety_passed = sum(
        result["safety_evaluation"]["passed"]
        for result in successful
    )

    field_summary = aggregate_field_accuracy(results)

    completed = (
        len(results) == len(cases)
        and len(successful) == len(cases)
    )

    report = {
        "evaluated_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "total_cases": len(cases),
        "attempted_cases": len(results),
        "successful_evaluations": len(successful),
        "completed": completed,
        "extraction_passed": extraction_passed,
        "safety_passed": safety_passed,
        "field_accuracy_summary": field_summary,
        "results": results,
    }

    OUTPUT_FILE.parent.mkdir(
        parents=True, exist_ok=True
    )

    OUTPUT_FILE.write_text(
        json.dumps(report, indent=4, ensure_ascii=False),
        encoding="utf-8",
    )

    print("\nROBUSTNESS EVALUATION SUMMARY")
    print("=" * 40)

    print(f"Completed: {completed}")
    print(f"Successful evaluations: {len(successful)}/{len(cases)}")
    print(f"Extraction passed: {extraction_passed}/{len(successful)}")
    print(f"Safety passed: {safety_passed}/{len(successful)}")

    print("\nFIELD-LEVEL ACCURACY")
    print("=" * 40)

    for field, stats in field_summary["metrics"].items():
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

    print(f"\nReport saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    run_robustness_benchmark()
