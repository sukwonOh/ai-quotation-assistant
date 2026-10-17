from pathlib import Path
from types import SimpleNamespace
import math
import os
import sys
import json

import streamlit as st
from dotenv import load_dotenv

# Project configuration

PROJECT_ROOT = Path(__file__).resolve().parents[1]

for path in (PROJECT_ROOT, PROJECT_ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

load_dotenv(PROJECT_ROOT / ".env")

# Import our existing AI extractor

from src.gemini_extractor import extract_enquiry_gemini
from enquiry_matcher import match_enquiry_to_catalogue
from quotation_module import create_full_quotation
from catalogue import load_catelogue, find_product_by_id
from quotation_safety import check_quotation_safety
from pdf_exporter import build_approved_quotation_pdf

CATALOGUE_PATH = (
    PROJECT_ROOT
    / "data"
    / "synthetic"
    / "product_catalogue.csv"
)

def normalize_unit(unit):
    return str(unit).strip().lower().replace("²", "2").replace(" ","")

def generate_quotation(extracted):
    """ Connect Gemini extraction to the existing quotation engine. """

    raw_items = extracted.get("items")

    if not isinstance(raw_items, list) or not raw_items:
        raise ValueError("No quotation items were extracted.")

    # Keep the original customer wording for safety checks
    extracted["source_text"] = enquiry_text

    # Step 1: Safety validation
    safety = check_quotation_safety(
        extracted,
        CATALOGUE_PATH
    )

    st.session_state.extracted_enquiry = extracted
    st.session_state.safety = safety

    # Stop unsafe enquiries before pricing
    if safety["status"] != "DRAFT":
        reasons = safety["errors"] + safety["warnings"]

        raise ValueError(
            f"Quotation {safety['status']}: "
            + "; ".join(reasons)
        )

    # Convert Gemini dictionaries into matcher-compatible objects
    structured_items = []

    for index, item in enumerate(raw_items, start=1):
        if not isinstance(item, dict):
            raise ValueError("No quotation items were extracted.")

    # Convert Gemini dictionaries into matcher-compatible objects
    structured_items = []

    for index, item in enumerate(raw_items, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Invalid item {index}.")

        description = str(item.get("description") or "").strip()
        unit = str(item.get("unit") or "").strip()

        try:
            quantity = float(item.get("quantity"))
        except (TypeError, ValueError):
            raise ValueError(f"Invalid quantity for item {index}.")

        if not description or not unit:
            raise ValueError(f"Missing description or unit for item {index}.")

        if not math.isfinite(quantity) or quantity <= 0:
            raise ValueError(f"Quantity must be positive for item {index}.")

        structured_items.append(
            SimpleNamespace(
                description = description,
                quantity = quantity,
                unit = unit
            )
        )

    structured_enquiry = SimpleNamespace(items = structured_items)

    # Match products using the existing module
    matched_itmes = match_enquiry_to_catalogue(
        structured_enquiry
    )

    # Never silently ignore unmatched items
    if len(matched_itmes) != len(structured_items):
        raise ValueError(
            "One or more products could not be matched. "
            "Manual review required."
        )

    # Check units against the actual catalogue
    catalogue = load_catelogue()

    for item in matched_itmes:
        product = find_product_by_id(
            catalogue,
            item["product_id"]
        )

        if product.empty:
            raise ValueError("Matched product was not found. ")

        catalogue_unit = product.iloc[0]["unit"]

        if normalize_unit(item["unit"]) != normalize_unit(catalogue_unit):
            raise ValueError(
                f"Unit mismatch for {item['product_name']}."
                "Manual review required."
            )
    # Prepare quotation engine input
    quotation_items = [
        {
            "product_id" : item["product_id"],
            "quantity" : item["quantity"]
        }
        for item in matched_itmes
    ]

    quotation = create_full_quotation(quotation_items)

    return matched_itmes, quotation

# Page configuration

st.set_page_config(
    page_title="AI Quotation Assistant",
    page_icon="🧾",
    layout="wide"
)

# Application title
st.title("🧾 AI Quotation Assistant")
st.write("AI-powered construction quotation system")

# Sidebar
with st.sidebar:
    st.header("Project Navigation")
    st.write("Step 1: Product Catalogue✅")
    st.write("Step 2: Enquiry Processing ✅")
    st.write("Step 3: AI Pipeline & Safety ✅")
    st.write("Step 4: Streamlit UI 🚧")


# Session state
default_state = {
    "extracted_enquiry": None,
    "matched_items": None,
    "quotation": None,
    "safety": None,
    "review_status": "PENDING",
    "reivew_details": None,
}

for key,value in default_state.items():
    if key not in st.session_state:
        st.session_state[key] = None



example_enquiry = """
Hi, my name is Daniel.

I need about 120 m2 of Standard Aluminium Cladding and 120 m2 of 50mm Insulation Board.

The project is located in Parramatta.
"""

st.header("1. Customer Enquiry")

with st.form("enquiry_form"):
    enquiry_text = st.text_area(
        "Enter customer enquiry:",
        value=example_enquiry,
        height = 200
    )

    submitted = st.form_submit_button(
        "Extract Enquiry (AI)",
        type = "primary"
    )

if submitted:
    # Clear previous enquiry and quotation
    st.session_state.extracted_enquiry = None
    st.session_state.matched_items = None
    st.session_state.quotation = None
    st.session_state.safety = None

    # Reset human approval for every new enquiry
    st.session_state.review_status = "PENDING"
    st.session_state.review_details = None

    # Clear previous reviewer input
    st.session_state["reviewer_name"] = ""
    st.session_state["review_confirm"] = False


    if not enquiry_text.strip():
        st.warning(
                "DRAFT ONLY - Safety validation completed. "
                "Human review and approval are required "
                "before sending this quotation."
            )

    elif not os.getenv("GEMINI_API_KEY"):
        st.error("GEMINI_API_KEY is missing.")

    else :
        try:
            with st.spinner("Extracting with Gemini AI..."):
                extracted = extract_enquiry_gemini(enquiry_text)

            if not isinstance(extracted, dict):
                raise ValueError("Gemini did not return a dictionary.")

            # Step 1: Preserve original customer enquiry
            extracted["source_text"] = enquiry_text

            # Step 2 : Run safety validation
            safety = check_quotation_safety(
                extracted,
                CATALOGUE_PATH
            )

            # Step 3: Save results to session state
            st.session_state.extracted_enquiry = extracted
            st.session_state.safety = safety

            st.success("AI extraction successful!")

        except Exception as error:
            st.error(f"AI extraction failed: {error}")

# Displat extracted information
if st.session_state.extracted_enquiry is not None:

    extracted = st.session_state.extracted_enquiry

    st.header("2. AI Extraction Results")
    st.json(extracted)

    # Safety Validation
    st.header("3. Safety Validation")

    safety = st.session_state.safety

    if safety is not None:
        status = safety["status"]

        if status == "DRAFT":
            st.success(
                "Safety status : DRAFT - "
                "Quotation calculation is permitted."
            )

        elif status == "HOLD":
            st.warning(
                "Safety status: HOLD - "
                "Clarification required before pricing"
            )

        elif status == "BLOCK":
            st.error(
                "Safety status: BLOCK - "
                "Quotation calculation is prohibited."
            )

        for error in safety["errors"]:
            st.error(error)

        for warning in safety["warnings"]:
            st.warning(warning)

        st.info("Human review is required")


    st.header("4. Product Matching & Quotation")

    if st.button(
        "Generate Quotation",
        type = "primary",
        disabled=(
            st.session_state.safety is None
            or st.session_state.safety["status"] != "DRAFT"
        )
    ):
        # Reset previous quotation
        st.session_state.matched_items = None
        st.session_state.quotation = None

        # Reset previous human approval
        st.session_state.review_status = "PENDING"
        st.session_state.review_details = None
        st.session_state["reviewer_name"] = ""
        st.session_state["review_confirm"] = False

        try:
            with st.spinner("Matching products and calculating..."):
                matched, quotation = generate_quotation(extracted)

            st.session_state.matched_items = matched
            st.session_state.quotation = quotation

            st.success("Draft quotation generated!")

        except Exception as error:
            st.error(f"Quotation failed: {error}")

# Display quotation results

if st.session_state.quotation is not None:

    quotation = st.session_state.quotation
    matched = st.session_state.matched_items

    st.subheader("Matched Products")
    st.dataframe(matched, hide_index=True)

    st.subheader("Quotation Details")

    rows = []

    for item in quotation["items"]:
        rows.append({
            "Product ID": item["product_id"],
            "Product" : item["product_name"],
            "Quantity": item["quantity"],
            "Unit" : item["unit"],
            "Total (AUD)" : item["total"]
        })

    st.dataframe(rows, hide_index=True)

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Subtotal",
        f"${quotation['subtotal']:,.2f}"
    )

    col2.metric(
        "Total",
        f"${quotation['total']:,.2f}"
    )

    st.warning(
        "DRAFT ONLY - Safety validation completed "
        "Human approval is required before export."
    )

    with st.expander("View Quotation JSON"):
        st.json(quotation)

    # Step 5: Human Review
    st.header("5. Human Review & Approval")

    st.info(
        "Please verify the customer details, project scope "
        "product quantities, prices, GST, and safety warnings "
        "before approving this quotation."
    )

    reviewer = st.text_input(
        "Reviewer Name",
        key = "reviewer_name"
    )

    confirmed = st.checkbox(
        "I have reviewed the quotation and confirmed "
        "the detials are correct.",
        key = "review_confirm"
    )

    can_approve = (
        st.session_state.safety is not None
        and st.session_state.safety["status"] == "DRAFT"
        and st.session_state.review_status == "PENDING"
        and bool(reviewer.strip())
        and confirmed
    )

    col_approve, col_reject = st.columns(2)

    with col_approve:
        if st.button(
            "Approve Quotation",
            type = "primary",
            disabled=not can_approve
        ):
            # Revalidate safety before approving
            latest_safety = check_quotation_safety(
                st.session_state.extracted_enquiry,
                CATALOGUE_PATH
            )

            if latest_safety["status"] == "DRAFT":
                from datetime import datetime, timezone

                st.session_state.review_status = "APPROVED"
                st.session_state.review_details = {
                    "reviewer": reviewer.strip(),
                    "approved_at_utc": datetime.now(
                        timezone.utc
                    ).isoformat()
                }

                st.success("Quotation approved!")

            else:
                st.session_state.safety = latest_safety
                st.error(
                    "Approval refuesd: safety validation failed."
                )

    with col_reject:
        if st.button(
            "Reject Quotation",
            disabled=(
                st.session_state.review_status != "PENDING"
            )
        ):
            st.session_state.review_status = "REJECTED"
            st.session_state.review_details = None

            st.rerun()

    # Display current review status
    status = st.session_state.review_status

    if status == "APPROVED":
        st.success("Review status: APPROVED")
        st.json(st.session_state.review_details)

    elif status == "REJECTED":
        st.error("Review status: REJECTED")

    else:
        st.warning("Review status: PENDING")

    # Step 6: Approved Quotation Export
    st.header("6. Approved Quotation Export")

    approved = (
        st.session_state.review_status == "APPROVED"
        and st.session_state.review_details is not None
        and st.session_state.safety is not None
        and st.session_state.safety["status"] == "DRAFT"
    )

    if approved:
        # Recheck safety before exporting
        latest_safety = check_quotation_safety(
            st.session_state.extracted_enquiry,
            CATALOGUE_PATH
        )

        if latest_safety["status"] != "DRAFT":
            st.error(
                "Export blocked: safety validation failed."
            )
        else:
            export_data = {
                "status": "APPROVED",
                "customer": (
                    st.session_state.extracted_enquiry.get(
                        "customer", {}
                    )
                ),
                "matched_itmes": st.session_state.matched_items,
                "quotation": st.session_state.quotation,
                "safety": latest_safety,
                "review": st.session_state.review_details
            }

            json_data = json.dumps(
                export_data,
                indent = 4,
                ensure_ascii = False
            )

            st.download_button(
                label = "Download Approved Quotation (JSON)",
                data = json_data,
                file_name = "approved_quotation.json",
                mime = "application/json"
            )

            # Step 4C.3.3 - PDF Export
            try:
                pdf_data = build_approved_quotation_pdf(
                    export_data
                )

                st.download_button(
                    label="Download Approved Quotation (PDF)",
                    data = pdf_data,
                    file_name= "approved_quotation.pdf",
                    mime = "application/pdf",
                    key = "download_approved_pdf"
                )

            except Exception as error:
                st.error(
                    f"PDF generation failed: {error}"
                )

    else :
        st.info(
            "Quotation export is available only "
            "after human approval."
        )
