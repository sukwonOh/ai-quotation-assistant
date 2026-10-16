import json
import math
from pathlib import Path

from quotation_safety import check_quotation_safety
from gemini_extractor import StructuredEnquiry
from enquiry_matcher import match_enquiry_to_catalogue
from quotation_module import create_full_quotation

# 1. Project paths

PROJECT_ROOT = Path(__file__).resolve().parents[1]

INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "test"
    / "gemini_enquiry_sample.json"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "test"
    / "quotation_from_gemini.json"
)

# 2. Load and validate Gemini extraction

def create_quotation_from_gemini():

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Gemini JSON not found: {INPUT_FILE}"
        )

    data = json.loads(
        INPUT_FILE.read_text(encoding="utf-8")
    )

    # Quotation Safety Validation
    safety = check_quotation_safety(
        data,
        PROJECT_ROOT / "data" / "synthetic"
        / "product_catalogue.csv"
    )

    print(f"Safety status: {safety['status']}")

    for warning in safety["warnings"]:
        print(f"WARNING: {warning}")

    if safety["status"] != "DRAFT":
        raise SystemExit(
            f"Quotation {safety['status']}: "
            + "; ".join(
                safety["errors"] + safety["warnings"]
            )
        )

    enquiry = StructuredEnquiry.model_validate(data)

    if not enquiry.items:
        raise ValueError("No quotation items found.")

    for item in enquiry.items:

        if(
            item.quantity is None
            or not math.isfinite(item.quantity)
            or item.quantity <= 0
        ):
            raise ValueError(
                f"Invalid quantity for {item.description}"
            )

        if item.unit not in ("m2", "m²"):
            raise ValueError(
                f"Unsupported unit for {item.description}: "
                f"{item.unit}"
            )

    # 3. Match products to the catalouge

    matched_items = match_enquiry_to_catalogue(
        enquiry
    )

    if len(matched_items) != len(enquiry.items):
        raise ValueError(
            "Some products could not be matched. "
            "Human review required."
        )

    # 4. Prepare items for pricing engine

    quotation_items = []

    for item in matched_items:
        quotation_items.append({
            "product_id": item["product_id"],
            "quantity": item["quantity"]
        })

    # 5. Generate quotation

    quotation = create_full_quotation(
        quotation_items
    )

    # 6. Save result with customer details

    result = {
        "customer": enquiry.customer.model_dump(),
        "project": enquiry.project.model_dump(),
        "matched_items": matched_items,
        "quotation" : quotation,
        "notes" : enquiry.notes,
        "safety" : safety,
        "review_required" : True
    }

    OUTPUT_FILE.parent.mkdir(
        parents = True,
        exist_ok = True
    )

    OUTPUT_FILE.write_text(
        json.dumps(
            result,
            indent = 4,
            ensure_ascii = False
        ),
        encoding = "utf-8"
    )

    return result

# 7. Excute

if __name__ == "__main__":

    result = create_quotation_from_gemini()

    print("\nGEMINI QUOTATION")
    print("=" * 50)

    #print("Available keys:", list(result.keys()))

    for item in result["matched_items"]:
        print(
            item["product_id"],
            " | ",
            item["product_name"],
            item["quantity"]
        )
    quotation = result["quotation"]

    print("-" * 50)
    print(f"Subtotal: ${quotation['subtotal']:.2f}")
    print(f"GST:      ${quotation['gst']:.2f}")
    print(f"Total:    ${quotation['total']:.2f}")

    print("\nHuman review required.")
    print(f"Quotation saved to: {OUTPUT_FILE}")
