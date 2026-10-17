""" Generate a PDF from an approved construction quotation. """

from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape
from datetime import datetime, timezone

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import(
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

def build_approved_quotation_pdf(export_data: dict) -> bytes:
    """ Creates PDF bytes from an approved quotation """

    # 1. Check approval
    if export_data.get("status") != "APPROVED":
        raise ValueError(
            "PDF export requires an approved quotation"
        )

    safety = export_data.get("safety") or {}


    if safety.get("status") != "DRAFT":
        raise ValueError(
            "PDF export blocked by quotation safety status."
        )

    review = export_data.get("review") or {}

    if not review.get("reviewer") or not review.get("approved_at_utc"):
        raise ValueError(
            "Reviewer and approval timestamp are required."
        )

    quotation = export_data.get("quotation") or {}
    items = quotation.get("items") or []

    if not items:
        raise ValueError("Quotation has no priced items.")


    # 2. Formatting helpers
    def safe_text(value):
        if value is None or value == "":
            return "Not provided"
        return escape(str(value))

    def money(value):
        try:
            return f"${float(value):,.2f}"
        except (TypeError, ValueError):
            raise ValueError(
                "Quotation contains an invalid price"
            ) from None

    # 3. PDF styles
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "QuoteTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=19,
        leading=23,
        textColor=colors.HexColor("#18324A"),
        spaceAfter=8,
    )

    heading_style = ParagraphStyle(
        "QuoteHeading",
        parent=styles["Heading2"],
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#18324A"),
        spaceBefore=14,
        spaceAfter=7,
    )

    cell_style = ParagraphStyle(
        "QuoteCell",
        parent=styles["BodyText"],
        fontSize=8.5,
        leading=11,
    )

    right_style = ParagraphStyle(
        "QuoteCellRight",
        parent=cell_style,
        alignment=TA_RIGHT,
    )

    customer = export_data.get("customer") or {}
    project = export_data.get("project") or {}

    # 4. Set up PDF
    buffer = BytesIO()

    page_width, _= A4
    margin = 40
    content_width = page_width -2 * margin

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=42,
        bottomMargin=48,
        title="Approved Construction Quotation",
    )

    story = [
        Paragraph("AI QUOTATION ASSISTANT", title_style),
        Paragraph(
            "APPROVED CONSTRUCTION QUOTATION",
            styles["Heading3"]
        ),
        Spacer(1,11),
        Paragraph("Customer &amp; project", heading_style),
    ]

    # 5. Customer and project details
    details = [
        [
            "Customer",
            Paragraph(safe_text(customer.get("name")), cell_style),
        ],
        [
            "Company",
            Paragraph(safe_text(customer.get("company")), cell_style),
        ],
        [
            "Email",
            Paragraph(safe_text(customer.get("email")), cell_style),
        ],
        [
            "Project address",
            Paragraph(safe_text(project.get("company")), cell_style),
        ],
        [
            "Project type",
            Paragraph(safe_text(project.get("company")), cell_style),
        ],
    ]

    detail_table = Table(
        details,
        colWidths=[110, content_width - 110],
        hAlign="LEFT",
    )

    detail_table.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("TOPPADDING", (0,0), (-1,-1), 6),
        (
            "LINEBELOW",
            (0,0),
            (-1,-2),
            0.3,
            colors.HexColor("#E2E8EE"),
        ),
        (
            "TEXTCOLOR",
            (0,0),
            (0,-1),
            colors.HexColor("#526372"),
        ),
    ]))

    story.extend([
        detail_table,
        Paragraph("Quotation items", heading_style),
    ])

    # 6, Quotation item table
    table_data = [[
        "Product ID",
        "Description",
        "Qty",
        "Unit",
        "Total (AUD)",
    ]]

    for item in items:
        table_data.append([
            Paragraph(
                safe_text(item.get("product_id")),
                cell_style,
            ),
            Paragraph(
                safe_text(item.get("product_name")),
                cell_style,
            ),
            Paragraph(
                safe_text(item.get("quantity")),
                right_style,
            ),
            Paragraph(
                safe_text(item.get("unit")),
                cell_style,
            ),
            Paragraph(
                money(item.get("total")),
                right_style,
            ),
        ])

    item_table = Table(
        table_data,
        colWidths=[
            75,
            content_width - 75 - 65 - 50 - 100,
            65,
            50,
            100,
        ],
        repeatRows=1,
        hAlign="LEFT",
    )

    item_table.setStyle(TableStyle([
        (
            "BACKGROUND",
            (0,0),
            (-1,0),
            colors.HexColor("#18324A"),
        ),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,0), 8),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("TOPPADDING", (0,0), (-1,-1), 9),
        ("BOTTOMPADDING", (0,0), (-1,-1), 9),
        ("LEFTPADDING", (0,0), (-1,-1), 7),
        ("RIGHTPADDING", (0,0), (-1,-1), 7),
        (
            "LINEBELOW",
            (0,1),
            (-1, -1),
            0.4,
            colors.HexColor("#E2E8EE"),
        ),
    ]))

    story.extend([
        item_table,
        Spacer(1, 15),
    ])

    # 7. Price summary
    summary = [
        ["Subtotal", money(quotation.get("subtotal"))],
        ["GST", money(quotation.get("gst"))],
        ["TOTAL (AUD)", money(quotation.get("total"))],
    ]

    summary_table = Table(
        summary,
        colWidths=[content_width - 155, 155],
    )

    summary_table.setStyle(TableStyle([
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, -1), (-1, -1), 12),
        (
            "LINEABOVE",
            (0, -1),
            (-1, -1),
            1,
            colors.HexColor("#18324A"),
        ),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))

    story.extend([
        summary_table,
        Paragraph("Approval record", heading_style),
    ])

    # 8. Approval information
    approved_at = str(review["approved_at_utc"])

    try:
        dt = datetime.fromisoformat(
            approved_at.replace("Z", "+00:00")
        )

        approved_at = dt.astimezone(
            timezone.utc
        ).strftime("%Y-%m-%d %H:%M UTC")

    except ValueError:
        pass

    story.extend([
        Paragraph(
            f"Reviewed by: {safe_text(review['reviewer'])}",
            cell_style,
        ),
        Paragraph(
            f"Approved at: {safe_text(approved_at)}",
            cell_style,
        ),
        Spacer(1, 12),
        Paragraph(
            "Human-approved quotation generated from an "
            "AI-assisted draft. Verify all commercial terms "
            "before sending to a customer.",
            cell_style,
        ),
    ])

    # 9. Footer
    def footer(canvas, doc):
        canvas.saveState()

        canvas.setStrokeColor(
            colors.HexColor("#DCE4EA")
        )

        canvas.line(
            margin,
            32,
            page_width - margin,
            32,
        )

        canvas.setFont("Helvetica", 8)

        canvas.setFillColor(
            colors.HexColor("#526372")
        )

        canvas.drawString(
            margin,
            20,
            "AI Quotation Assistant | Approved copy",
        )

        canvas.drawRightString(
            page_width - margin,
            20,
            f"Page {doc.page}",
        )

        canvas.restoreState()

    # 10. Generate PDF
    document.build(
        story,
        onFirstPage=footer,
        onLaterPages=footer,
    )

    return buffer.getvalue()


# 11. Test PDF generation
if __name__ == "__main__":

    sample = {
        "status": "APPROVED",

        "customer": {
            "name": "Alex (Demo)",
            "company": "Example Construction",
            "email": "alex@example.com",
        },

        "project": {
            "address": "Parramatta, Sydney",
            "project_type": "commercial",
        },

        "quotation": {
            "items": [
                {
                    "product_id": "CLD001",
                    "product_name": "Standard Aluminium Cladding",
                    "quantity": 120,
                    "unit": "m2",
                    "total": 18282.00,
                },
                {
                    "product_id": "INS001",
                    "product_name": "50mm Insulation Board",
                    "quantity": 120,
                    "unit": "m2",
                    "total": 4633.20,
                },
            ],
            "subtotal": 20832.00,
            "gst": 2083.20,
            "total": 22915.20,
        },

        "safety": {
            "status": "DRAFT",
        },

        "review": {
            "reviewer": "Demo Reviewer",
            "approved_at_utc": "2026-10-16T11:00:12+00:00",
        },
    }

    output_path = (
        Path(__file__).resolve().parents[1]
        / "data"
        / "test"
        / "test_approved_quotation.pdf"
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_bytes(
        build_approved_quotation_pdf(sample)
    )

    print(f"PDF created: {output_path}")
