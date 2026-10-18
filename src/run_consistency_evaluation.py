"""Run repeated Gemini extraction and consistency evaluation."""

import json
import time
from datetime import datetime, timezone
from pathlib import Path

from gemini_extractor import extract_enquiry_gemini
from gemini_evaluator import (
    load_all_test_cases,
    evaluate_case,
    evaluate_safety_case,
)
from consistency_evaluator import evaluate_consistency


PROJECT_ROOT = Path(__file__).resolve().parents[1]

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "test"
    / "consistency_evaluation_report.json"
)

CASE_IDS = (
    "standard",
    "informal",
    "missing_quantity",
)

RUNS_PER_CASE = 3
DELAY_SECONDS = 10


def run_consistency_benchmark():
    """Repeat selected benchmark enquiries and evaluate agreement."""

    cases = {
        case["id"]: case
        for case in load_all_test_cases()
    }

    report = {
        "evaluated_at_utc": datetime.now(timezone.utc).isoformat(),
        "runs_per_case": RUNS_PER_CASE,
        "delay_seconds": DELAY_SECONDS,
        "cases": {},
    }

    stopped_early = False

    for case_id in CASE_IDS:
        case = cases[case_id]
        extractions = []
        run_results = []

        print(f"\nTesting case: {case_id}")
        print("=" * 40)

        for run_number in range(1, RUNS_PER_CASE + 1):
            print(f"Run {run_number}/{RUNS_PER_CASE}")

            try:
                extracted = extract_enquiry_gemini(case["text"])

                extraction_result = evaluate_case(
                    case, extracted
                )

                safety_result = evaluate_safety_case(
                    case, extracted
                )

                extractions.append(extracted)

                run_results.append({
                    "run": run_number,
                    "extraction_passed": extraction_result["passed"],
                    "safety_passed": safety_result["passed"],
                    "safety_status": safety_result["actual_status"],
                })

                print(
                    f"Extraction: "
                    f"{'PASS' if extraction_result['passed'] else 'FAIL'}"
                )

                print(
                    f"Safety: {safety_result['actual_status']}"
                )

            except Exception as error:
                print(f"API or evaluation error: {error}")

                run_results.append({
                    "run": run_number,
                    "error": str(error),
                })

                # Stop rather than repeatedly calling a failing API.
                stopped_early = True
                break

            # Space out requests to reduce the chance of rate limits.
            if (
                case_id != CASE_IDS[-1]
                or run_number != RUNS_PER_CASE
            ):
                time.sleep(DELAY_SECONDS)

        consistency = (
            evaluate_consistency(extractions)
            if len(extractions) >= 2
            else None
        )

        report["cases"][case_id] = {
            "successful_api_runs": len(extractions),
            "requested_runs": RUNS_PER_CASE,
            "consistency": consistency,
            "runs": run_results,
        }

        if consistency is not None:
            print(
                f"Pairwise agreement: "
                f"{consistency['agreement_percent']}%"
            )
        else:
            print("Pairwise agreement: Not available")

        if stopped_early:
            break

    report["completed"] = not stopped_early

    OUTPUT_FILE.parent.mkdir(
        parents=True, exist_ok=True
    )

    OUTPUT_FILE.write_text(
        json.dumps(report, indent=4, ensure_ascii=False),
        encoding="utf-8",
    )

    print("\nCONSISTENCY EVALUATION COMPLETE")
    print("=" * 40)
    print(f"Completed: {report['completed']}")
    print(f"Report saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    run_consistency_benchmark()
