"""Evaluate consistency across repeated LLM extractions."""

import math
import re


def normalise_text(value):
    """Normalise text for consistent comparisons."""
    return " ".join(
        re.findall(r"[a-z0-9]+", str(value or "").lower())
    )


def normalise_unit(value):
    """Treat m² and m2 as equivalent."""
    return (
        str(value or "")
        .strip()
        .lower()
        .replace("²", "2")
        .replace(" ", "")
    )


def canonicalise_extraction(extracted):
    """Convert an extraction into a comparable representation."""

    if not isinstance(extracted, dict):
        raise ValueError("Extraction must be a dictionary.")

    customer = extracted.get("customer") or {}
    project = extracted.get("project") or {}
    items = extracted.get("items")

    if (
        not isinstance(customer, dict)
        or not isinstance(project, dict)
        or not isinstance(items, list)
    ):
        raise ValueError("Invalid extraction structure.")

    normalised_items = []

    for item in items:
        if not isinstance(item, dict):
            raise ValueError("Invalid extracted product.")

        quantity = item.get("quantity")

        if quantity is not None:
            if (
                isinstance(quantity, bool)
                or not isinstance(quantity, (int, float))
                or not math.isfinite(quantity)
            ):
                raise ValueError("Invalid extracted quantity.")

            quantity = float(quantity)

        normalised_items.append(
            (
                normalise_text(item.get("description")),
                quantity,
                normalise_unit(item.get("unit")),
            )
        )

    # Product order should not affect consistency.
    normalised_items.sort(
        key=lambda item: (item[0], item[2], str(item[1]))
    )

    return (
        normalise_text(customer.get("name")),
        normalise_text(project.get("address")),
        tuple(normalised_items),
    )


def evaluate_consistency(extractions):
    """Measure pairwise agreement between repeated outputs."""

    if not isinstance(extractions, list) or len(extractions) < 2:
        raise ValueError("At least two extraction runs are required.")

    outputs = [
        canonicalise_extraction(extracted)
        for extracted in extractions
    ]

    runs = len(outputs)
    total_pairs = runs * (runs - 1) // 2

    agreeing_pairs = sum(
        outputs[i] == outputs[j]
        for i in range(runs)
        for j in range(i + 1, runs)
    )

    return {
        "runs": runs,
        "agreeing_pairs": agreeing_pairs,
        "total_pairs": total_pairs,
        "agreement_percent": round(
            100 * agreeing_pairs / total_pairs, 2
        ),
        "distinct_outputs": len(set(outputs)),
    }
