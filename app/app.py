from pathlib import Path
import math
import os
import sys
import json
import streamlit as st
import hmac
import time

from dotenv import load_dotenv

# Project configuration

PROJECT_ROOT = Path(__file__).resolve().parents[1]

for path in (PROJECT_ROOT, PROJECT_ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

load_dotenv(PROJECT_ROOT / ".env")

# Import our existing AI extractor

from src.gemini_extractor import extract_enquiry_gemini
from quotation_safety import check_quotation_safety
from quotation_service import generate_quotation
from pdf_exporter import build_approved_quotation_pdf

CATALOGUE_PATH = (
    PROJECT_ROOT
    / "data"
    / "synthetic"
    / "product_catalogue.csv"
)

# Page configuration

st.set_page_config(
    page_title="AI Quotation Assistant",
    page_icon="🧾",
    layout="wide"
)


# Step 5D - Demo access and cloud secrets

try:
    cloud_api_key = st.secrets.get("GEMINI_API_KEY")
    cloud_password = st.secrets.get("DEMO_PASSWORD")
except FileNotFoundError:
    cloud_api_key = None
    cloud_password = None

# Support Streamlit Cloud and local .env
if cloud_api_key:
    os.environ["GEMINI_API_KEY"] = str(cloud_api_key)

demo_password = cloud_password or os.getenv("DEMO_PASSWORD")

if not demo_password:
    st.error("Demo access is not configured.")
    st.stop()

# Restrict access to the application
if not st.session_state.get("demo_authenticated", False):

    st.title("AI Quotation Assistant")
    st.info("This portfolio demonstration requires access.")

    with st.form("demo_login"):
        entered_password = st.text_input(
            "Demo Password",
            type="password"
        )
        login_clicked = st.form_submit_button("Enter Demo")

    if login_clicked:
        if hmac.compare_digest(
            entered_password,
            str(demo_password)
        ):
            st.session_state.demo_authenticated = True
            st.rerun()
        else:
            st.error("Incorrect password.")

    st.stop()

# Application title
st.title("🧾 AI Quotation Assistant")
st.write("AI-powered construction quotation system")

# Sidebar
with st.sidebar:
    st.header("🧾 AI Quotation Assistant")
    st.caption("Construction Quotation Demo")

    st.divider()

    st.subheader("About this application")

    st.write(
        "This prototype uses Google Gemini to extract "
        "information from construction enquiries and "
        "Python to generate quotations."
    )

    st.divider()

    st.subheader("How to use")

    st.markdown(
        """
        1. Enter a customer enquiry
        2. Extract information using Gemini
        3. Review safety and pricing
        4. Approve the quotation
        5. Download JSON or PDF
        """
    )

    st.divider()

    st.subheader("Demo limitations")

    st.caption(
        "Uses synthetic catalogue prices. "
        "Human approval is required."
    )

    st.divider()

    st.link_button(
        "View on GitHub",
        "https://github.com/sukwonOh/ai-quotation-assistant"
    )

# Session state management.
DEFAULT_STATE = {
    "extracted_enquiry": None,
    "matched_items": None,
    "quotation": None,
    "safety": None,
    "review_status": "PENDING",
    "review_details": None,
}

# Initialise each value only once per session
for key, value in DEFAULT_STATE.items():
    if key not in st.session_state:
        st.session_state[key] = value

def reset_review_state():
    """ Reset Human approval information. """

    st.session_state.review_status = "PENDING"
    st.session_state.review_details = None

    st.session_state["reviewer_name"] = ""
    st.session_state["reviewer_confirm"] = False

def reset_quotation_state():
    """ Clear quotation and approval information. """

    st.session_state.matched_items = None
    st.session_state.quotation = None

    reset_review_state()

def reset_enquiry_state():
    """ Clear all results from the previous enquiry. """

    st.session_state.extracted_enquiry = None
    st.session_state.safety = None

    reset_quotation_state()

example_enquiry = """
Hi, my name is Alex from Example Construction.

We are renovating a commercial property in Parramatta, Sydney.

Could you please provide a quotation for:

- 120 m2 of Standard Aluminium Cladding
- 120 m2 of 50mm Insulation Board

Please include installation.

Thanks,
Alex
"""

# Step 5D.4B - Gemini API usage protection

MAX_ENQUIRY_CHARS = 3000
MAX_AI_REQUESTS = 5
AI_COOLDOWN_SECONDS = 30

# Track requests within the current Streamlit session
if "ai_request_count" not in st.session_state:
    st.session_state.ai_request_count = 0

if "last_ai_request_time" not in st.session_state:
    st.session_state.last_ai_request_time = None

st.header("1. Customer Enquiry")

with st.form("enquiry_form"):
    enquiry_text = st.text_area(
        "Enter customer enquiry:",
        value=example_enquiry,
        height = 200,
        max_chars = MAX_ENQUIRY_CHARS
    )

    submitted = st.form_submit_button(
        "Extract Enquiry (AI)",
        type = "primary"
    )

if submitted:
    # Clear previous enquiry, quotation, and approval
    reset_enquiry_state()

    current_time = time.monotonic()
    last_request = st.session_state.last_ai_request_time

    # 1. Validate enquiry input
    if not enquiry_text.strip():
        st.warning("Please enter a customer enquiry.")

    elif len(enquiry_text) > MAX_ENQUIRY_CHARS:
        st.error("Customer enquiry exceeds the character limit.")

    # 2. Check session request limit
    elif st.session_state.ai_request_count >= MAX_AI_REQUESTS:
        st.error(
            "Demo request limit reached. "
            "This session cannot submit more AI requests."
        )

    # 3. Check cooldown
    elif (
        last_request is not None
        and current_time - last_request < AI_COOLDOWN_SECONDS
    ):
        remaining = math.ceil(
            AI_COOLDOWN_SECONDS - (current_time - last_request)
        )

        st.warning(
            f"Please wait {remaining} seconds "
            "before making another AI request."
        )

    # 4. Check API key
    elif not os.getenv("GEMINI_API_KEY"):
        st.error("GEMINI_API_KEY is missing.")

    else:
        # Count the attempt before calling Gemini
        st.session_state.ai_request_count += 1
        st.session_state.last_ai_request_time = current_time

        try:
            with st.spinner("Extracting with Gemini AI..."):
                extracted = extract_enquiry_gemini(enquiry_text)

            if not isinstance(extracted, dict):
                raise ValueError(
                    "Gemini did not return a dictionary."
                )

            # Preserve original enquiry
            extracted["source_text"] = enquiry_text

            # Safety validation
            safety = check_quotation_safety(
                extracted,
                CATALOGUE_PATH
            )

            # Save results
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
        reset_quotation_state()

        try:
            with st.spinner("Matching products and calculating..."):
                matched, quotation = generate_quotation(
                    extracted,
                    enquiry_text
                )

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
                 st.session_state.extracted_enquiry.get("customer") or {}
             ),
            "project": (
                 st.session_state.extracted_enquiry.get("project") or {}
             ),
            "matched_items": st.session_state.matched_items,
            "quotation": st.session_state.quotation,
            "safety": latest_safety,
            "review": st.session_state.review_details,
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
