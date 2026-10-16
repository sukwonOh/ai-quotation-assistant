import json
from pathlib import Path
from catalogue import load_catelogue, validate_catalogue, find_product_by_id

def calculate_item(product, quantity):
    """Calculate quotation price for one product."""

    material_price = product["material_price"]
    labour_price = product["labour_price"]
    waste_factor = product["waste_factor"]
    gst_rate = product["gst_rate"]

    # Waste applies to material only
    material_quantity = quantity * (1 + waste_factor)

    material_cost = material_quantity * material_price
    labour_cost = quantity * labour_price

    subtotal = material_cost + labour_cost
    gst = subtotal * gst_rate
    total = subtotal + gst

    return {
        "product_id": product["product_id"],
        "product_name": product["product_name"],
        "quantity": quantity,
        "unit": product["unit"],
        "material_quantity": round(material_quantity, 2),
        "material_cost": round(material_cost, 2),
        "labour_cost": round(labour_cost, 2),
        "subtotal": round(subtotal, 2),
        "gst": round(gst, 2),
        "total": round(total, 2),
    }

def create_quotation(product_id, quantity):
    """Create a quotation for one product"""

    catalogue = load_catelogue()
    validate_catalogue(catalogue)

    result = find_product_by_id(
        catalogue,
        product_id
    )

    if result.empty:
        raise ValueError(
            f"Product not found: {product_id}"
        )

    product = result.iloc[0]

    if not product["active"]:
        raise ValueError(
            f"Product is inactive: {product_id}"
        )

    if quantity <= 0:
        raise ValueError(
            "Quantity must be greater than 0."
        )

    return calculate_item(
        product,
        quantity
    )

def create_full_quotation(items):
    """Create a quotation containing multiple products."""

    quotation_items = []

    subtotal = 0
    gst = 0
    total = 0

    for item in items:
        quotation_item = create_quotation(
                product_id= item["product_id"],
                quantity= item["quantity"]
            )

        quotation_items.append(quotation_item)

        subtotal += quotation_item["subtotal"]
        gst += quotation_item["gst"]
        total += quotation_item["total"]

    return {
        "items": quotation_items,
        "subtotal": round(subtotal, 2),
        "gst": round(gst, 2),
        "total": round(total, 2),
    }

def save_quotation(quotation, filename="quotation_sample.json"):
    """Save quotation as a JSON file."""

    project_root = Path(__file__).resolve().parents[1]

    output_folder = (
        project_root
        / "data"
        / "test"
    )

    output_folder.mkdir(
        parents = True,
        exist_ok = True
    )

    output_path = output_folder / filename

    with open(
        output_path,
        "w",
        encoding = "utf-8"
    ) as file:
        json.dump(
            quotation,
            file,
            indent = 4
        )

    print(f"\nQuotation saved to:")
    print(output_path)

if __name__ == "__main__":

    items = [
        {
            "product_id": "CLD001",
            "quantity": 120
        },
        {
            "product_id": "INS001",
            "quantity": 120
        }
    ]

    quotation = create_full_quotation(items)

    print("\nFULL QUOTATION")
    print("=" * 50)

    for item in quotation["items"]:
        print(
            f'{item["product_id"]} | '
            f'{item["product_name"]} | '
            f'{item["quantity"]} {item["unit"]} | '
            f'${item["total"]: .2f}'
        )

    print("-" * 50)

    print(f'Subtotal: ${quotation["subtotal"]: .2f}')
    print(f'GST: ${quotation["gst"]: .2f}')
    print(f'TOTAL: ${quotation["total"]: .2f}')

    save_quotation(quotation)
