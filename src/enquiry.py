from dataclasses import dataclass, asdict
from pathlib import Path
import json

@dataclass
class CustomerInfo:
    name: str | None = None
    company: str | None = None
    email: str | None = None
    phone: str | None = None

@dataclass
class ProjectInfo:
    address: str | None = None
    project_type: str | None = None

@dataclass
class EnquiryItem:
    description: str
    quantity: float | None = None
    unit: str | None = None

@dataclass
class StructuredEnquiry:
    customer: CustomerInfo
    project: ProjectInfo
    items: list[EnquiryItem]
    source_text: str
    notes: str | None = None

def validate_enquiry(enquiry: StructuredEnquiry) -> bool:
    """ Validate the structed customer enquiry """

    if not enquiry.source_text.strip():
        raise ValueError("Source enquiry text cannot be empty.")

    if not enquiry.items:
        raise ValueError("Enquiry must contain at least one requested item.")

    for item in enquiry.items:

        if not item.description.strip():
            raise ValueError("Item description cannot be empty.")

        if item.quantity is not None and item.quantity <= 0:
            f"Quantity must be greater than zero: {item.description}"

    print("Enquiry validation successful✅")

    return True

def save_enquiry_json(
        enquiry: StructuredEnquiry,
        output_path: str
) -> None:
    """ Save structured enquiry as Json """

    validate_enquiry(enquiry)
    output_file = Path(output_path)

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        output_file,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            asdict(enquiry),
            file,
            indent=2,
            ensure_ascii=False
        )

    print(f"Structured enquiry saved to:\n{output_file}")

if __name__ == "__main__":

    sample_text = """
    Hi,

    We are renovating a hotel and need approximately
    120 m2 of standard aluminium cladding and
    120 m2 of 50mm insulation board.

    The project is located in Parramatta.

    Please provide a quotation.

    Thanks,
    Daniel
    ABC Builders

    """

    sample_enquiry = StructuredEnquiry(

        customer=CustomerInfo(
            name="Daniel",
            company="ABC Builders"
        ),

        project=ProjectInfo(
            address="Parramatta",
            project_type="Hotel renovation"
        ),

        items=[
            EnquiryItem(
                description="Standard Aluminum Cladding",
                quantity=120,
                unit="m2"
            ),

            EnquiryItem(
                description="50mm Insulation Board",
                quantity=120,
                unit="m2"
            )
        ],

        source_text=sample_text,
        notes="Customer requested a quotation"
    )

    save_enquiry_json(
        sample_enquiry,
        "data/test/enquiry_sample.json"
    )
