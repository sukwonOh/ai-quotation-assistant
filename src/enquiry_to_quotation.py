from enquiry_extractor import(
    load_enquiry_text,
    extract_enquiry,
)

from enquiry_matcher import(
    match_enquiry_to_catalogue,
)

from quotation_module import(
    create_full_quotation,
    save_quotation,
)

def create_quotation_from_enquiry(
        enquiry_file : str
):
    """
    Complete pipeline:

    Raw customer enquiry
    ->
    Structured enquiry
    ->
    Catalogue matching
    ->
    Full quotation
    """

    # Step 1: Load raw customer enquiry
    raw_text = load_enquiry_text(
        enquiry_file
    )

    # Step 2: Convert raw text into structured data
    structured_enquiry = extract_enquiry(
        raw_text
    )

    # Step 3 : Match extracted products
    # Against the catalogue
    matched_items = match_enquiry_to_catalogue(
        structured_enquiry
    )

    if not matched_items:
        raise ValueError(
            "No enquiry items could be matched"
            "to the product catalogue."
        )

    # Step 4: Prepare data for quotation.py
    quotation_items = []

    for item in matched_items:

        quotation_items.append(
            {
                "product_id" : item["product_id"],
                "quantity" : item["quantity"]
            }
        )

    # Step 5: Calculate quotation
    quotation = create_full_quotation(
        quotation_items
    )

    return quotation

if __name__ == "__main__" :

    input_file = (
        "data/raw/customer_enquiry_001.txt"
    )

    quotation = create_quotation_from_enquiry(
        input_file
    )

    print("\nAUTOMATIC QUOTATION")
    print("=" * 50)

    for item in quotation["items"]:

        print(
            f"{item['product_id']} | "
            f"{item['product_name']} | "
            f"{item['quantity']} | "
            f"{item['total']:.2f} "
        )

        print("_" * 50)

        print(
            f"Subtotal: $"
            f"{quotation['subtotal']:.2f}"
        )

        print(
            f"GST : $ "
            f"{quotation['gst']:.2f}"
        )


        print(
            f"TOTAL : $ "
            f"{quotation['total']:.2f}"
        )

        save_quotation(
            quotation,
            filename = "quotation_from_enquiry.json"
        )
