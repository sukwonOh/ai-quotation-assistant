import re
from pathlib import Path

from enquiry import (
    CustomerInfo,
    ProjectInfo,
    EnquiryItem,
    StructuredEnquiry,
    save_enquiry_json,
)

def load_enquiry_text(file_path: str) -> str:
    """ Load raw customer enquiry text from a file """

    path = Path(file_path)

    if not path.exists():
        raise FileExistsError(f"Enquiry file not found: {file_path}")

    with open(path, "r", encoding="utf-8") as file:
        text = file.read()

    if not text.strip():
        raise ValueError("Customer enquiry is empty.")

    return text

def extract_quantity(
        text: str,
        product_keyword: str
) -> float | None:
    """
    Extract quantity appearing before a product keyword.

    Example:
    120 m2 of standard aluminum cladding
    """

    pattern = (
        rf"\d+(?:\.\d+)?"
        rf"\s*(?:m2|m²|sqm)"
        rf"\s*(?:of\s+)?"
        rf"{re.escape(product_keyword)}"
    )

    match = re.search(
        pattern,
        text,
        re.IGNORECASE
    )

    if match:
        number_match = re.search(
            r"\d+(?:\.\d+)?",
            match.group(0)
        )

        if number_match:
            return float(number_match.group(0))

    return None

def extract_enquiry(text: str) -> StructuredEnquiry:
    """
    Convert raw customer enquiry text into structured data.

    This is a temporary rule-based implementation.
    Later this function will be replaced by an LLM.
    """

    items = []

    cladding_quantity = extract_quantity(
        text,
        "standard aluminium cladding"
    )

    if cladding_quantity is not None:
        items.append(
            EnquiryItem(
                description="Standard Aluminium Cladding",
                quantity=cladding_quantity,
                unit="m2"
            )
        )

    insulation_quantity = extract_quantity(
        text,
        "50mm insulation board"
    )

    if insulation_quantity is not None:
        items.append(
            EnquiryItem(
                description="50mm Insulation Board",
                quantity=insulation_quantity,
                unit="m2"
            )
        )

    customer = CustomerInfo(
    name="Daniel" if "Daniel" in text else None,
    company="ABC Builders" if "ABC Builders" in text else None
    )

    project = ProjectInfo(
    address="Parramatta" if "Parramatta" in text else None,
    project_type=(
        "Hotel renovation"
        if "hotel" in text.lower()
        else None
    )
)

    return StructuredEnquiry(
        customer=customer,
        project=project,
        items=items,
        source_text=text,
        notes=None
    )

if __name__ == "__main__":

    input_file = "data/raw/customer_enquiry_001.txt"

    raw_text = load_enquiry_text(input_file)

    structured_enquiry = extract_enquiry(raw_text)

    print("\nSTRUCTED ENQUIRY")
    print("=" * 50)

    print(
        f"Customer: "
        f"{structured_enquiry.customer.name}"
    )

    print(
        f"Project location: "
        f"{structured_enquiry.project.address}"
    )

    print("\nITEMS")

    for item in structured_enquiry.items:
        print(
            f"{item.description}"
            f"{item.quantity} {item.unit}"
        )

    save_enquiry_json(
        structured_enquiry,
        "data/test/extracted_enquiry.json"
    )
