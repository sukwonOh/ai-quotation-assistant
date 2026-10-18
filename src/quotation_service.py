""" Business logic for generating construction quotations. """

import math
from pathlib import Path
from types import SimpleNamespace

from catalogue import load_catelogue, find_product_by_id
from enquiry_matcher import match_enquiry_to_catalogue
from quotation_module import create_full_quotation
from quotation_safety import check_quotation_safety

CATALOGUE_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "synthetic"
    / "product_catalogue.csv"
)

def normalize_unit(unit):
    return str(unit).strip().lower().replace("²", "2").replace(" ", "")

def generate_quotation(extracted, current_enquiry_text):
    """ Validate and convert a structured enquiry into a quotation. """

    if not isinstance(extracted, dict):
        raise ValueError("Invalid extracted enquiry.")

    # Ensure that the enquiry has not changed since extraction
    original_text = extracted.get("source_text")

    if(
        not isinstance(original_text, str)
        or not isinstance(current_enquiry_text, str)
        or original_text.strip() != current_enquiry_text.strip()
    ):
        raise ValueError(
            "Customer enquiry has changed. "
            "Please run AI extraction again before generating a quotation."
        )

    raw_items = extracted.get("items")

    if not isinstance(raw_items, list) or not raw_items:
        raise ValueError("No quotation items were extracted.")

    # Check safety before pricing
    safety = check_quotation_safety(extracted, CATALOGUE_PATH)

    if safety["status"] != "DRAFT":
        reasons = safety["errors"] + safety["warnings"]
        raise ValueError(
            f"Quotation {safety['status']}: " + "; ". join(reasons)
        )

    # Convert extracted data into matcher-compatible objects
    structured_items = []

    for index, item in enumerate(raw_items, start=1):
        if not isinstance(item,dict):
            raise ValueError(f"Invalid item {index}.")

        description = str(item.get("description") or "").strip()
        unit = str(item.get("unit") or "").strip()

        try:
            quantity = float(item.get("quantity"))
        except (TypeError, ValueError):
            raise ValueError(
                f"Invalid quantity for item {index}."
            ) from None

        if not description or not unit:
            raise ValueError(
                f"Missing description or unit for item {index}."
            )

        if not math.isfinite(quantity) or quantity <= 0:
            raise ValueError(
                f"Quantity must be positive for item {index}."
            )

        structured_items.append(
            SimpleNamespace(
                description = description,
                quantity = quantity,
                unit = unit,
            )
        )

    # Match products
    structured_enquiry = SimpleNamespace(items = structured_items)
    matched_items = match_enquiry_to_catalogue(structured_enquiry)

    if len(matched_items) != len(structured_items):
        raise ValueError(
            "One or more products could not be matched. "
            "Manual review required."
        )

    # Validate catalogue units
    catalogue = load_catelogue()

    for item in matched_items:
        product = find_product_by_id(
            catalogue, item["product_id"]
        )

        if product.empty:
            raise ValueError("Matched product was not found.")

        catalogue_unit = product.iloc[0]["unit"]

        if normalize_unit(item["unit"]) != normalize_unit(catalogue_unit):
            raise ValueError(
                f"Unit mismatch for {item['product_name']}. "
                "Manual review required."
            )

    # Generate deterministic quotation
    quotation_items = [
        {
            "product_id": item["product_id"],
            "quantity": item["quantity"],
        }
        for item in matched_items
    ]

    quotation = create_full_quotation(quotation_items)

    return matched_items, quotation
