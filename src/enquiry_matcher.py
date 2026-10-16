from catalogue import(
    load_catelogue,
    validate_catalogue,
    find_product_by_name,
)

from enquiry_extractor import(
    load_enquiry_text,
    extract_enquiry,
)

def match_enquiry_to_catalogue(structured_enquiry):
    """ Match extracted enquiry items with products in the product catalogue. """

    catalogue = load_catelogue()
    validate_catalogue(catalogue)
    matched_items = []

    for item in structured_enquiry.items:
        match = find_product_by_name(
            catalogue,
            item.description
        )

        if match.empty:
            print(
                f"❌ No catalogue match: "
                f"{item.description}"
            )

            continue

        product = match.iloc[0]
        matched_item = {
            "product_id" : product["product_id"],
            "product_name" : product["product_name"],
            "quantity" : item.quantity,
            "unit" : item.unit
        }

        matched_items.append(matched_item)

    return matched_items

if __name__ == "__main__":

    input_file = "data/raw/customer_enquiry_001.txt"
    raw_text = load_enquiry_text(input_file)
    structured_enquiry = extract_enquiry(raw_text)
    matched_items = match_enquiry_to_catalogue(
        structured_enquiry
    )

    print("\nCATALOGUE MATCHES")
    print("=" * 50)

    for item in matched_items:

        print(
            f"{item['product_id']} | "
            f"{item['product_name']} | "
            f"{item['quantity']} {item['unit']}"
        )
