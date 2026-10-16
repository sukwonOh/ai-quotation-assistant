import csv
import math
import re
from pathlib import Path

# 1. Text normalisation

def normalise(text):
    return re.sub(
        r"[^a-z0-9]+", "",
        str(text or "").lower()
    )

# 2. Load allowed catalogue products

def load_product_names(catalouge_path):
    with Path(catalouge_path).open(
        encoding="utf-8-sig", newline=""
    ) as file:

        reader = csv.DictReader(file)

        columns = {
            normalise(name): name
            for name in (reader.fieldnames or [])
        }

        name_column = next(
            (
                columns[key]
                for key in (
                    "productname",
                    "name",
                    "itemname",
                    "description"
                )
                if key in columns
            ),
            None
        )

        if name_column is None:
            raise ValueError(
                "Product name column not found. "
            )

        return {
            normalise(row[name_column])
            for row in reader
            if row.get(name_column)
        }

# 3. Quotation safety checks

def check_quotation_safety(enquiry, catalogue_path):

    errors = []
    warnings = []

    known_products = load_product_names(
        catalogue_path
    )

    items = enquiry.get("items") or []

    if not isinstance(items, list) or not items:
        errors.append("No products provided.")
        items = []

    for index, item in enumerate(items, start=1):

        if not isinstance(item,dict):
            errors.append(
                f"Item {index}: invalid data format."
            )

            continue

        description = item.get("description")
        quantity = item.get("quantity")
        unit = item.get("unit")

        # Check the catalouge
        if normalise(description) not in known_products:
            errors.append(
                f"Unknown product: {description}"
            )

        # Check quantity
        if (
            isinstance(quantity, bool)
            or not isinstance(quantity, (int, float))
            or not math.isfinite(quantity)
            or quantity <= 0
        ):
            errors.append(
                f"Invalid quantity for {description}"
            )

        # Check units
        if unit not in ("m2", "m²"):
            errors.append(
                f"Unsupported unit : {unit}"
            )

    # 4. Dectect uncertain quantities

    source_text = str(
        enquiry.get("source_text") or ""
    )

    notes = str(
        enquiry.get("notes") or ""
    )

    source_words = set(
        re.findall("[a-z]+", source_text.lower())
    )

    approximate_words = {
        "about",
        "roughly",
        "around",
        "approximately",
        "approx",
        "estimated"
    }

    approximate = bool(
        source_words & approximate_words
    )

    if approximate:
        warnings.append(
            "Approximate quantity: confirm measurements."
        )

    # 5. Detect installation requirements

    full_test = source_text + " " + notes

    full_words = re.findall(
        "[a-z]+", full_test.lower()
    )

    installation_words = {
        "installation",
        "install",
        "installing",
        "labour",
        "labor"
    }

    installation = (
        bool(set(full_words) & installation_words)
        or "supply and fit" in " ".join(full_words)
    )

    if installation:
        warnings.append(
            "Installation scope and labour need review."
        )

    # 6. Decide whether to proceed

    if errors:
        status = "BLOCK"

    elif approximate:
        status = "HOLD"

    else:
        status = "DRAFT"

    return {
        "status": status,
        "errors": errors,
        "warnings": warnings,
        "review_required": True
    }
