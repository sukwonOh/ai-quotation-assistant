
import copy
import unittest

from src.pdf_exporter import build_approved_quotation_pdf


class TestPDFExporter(unittest.TestCase):

    def setUp(self):
        self.sample = {
            "status": "APPROVED",
            "customer": {
                "name": "Alex",
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
                    }
                ],
                "subtotal": 16620.00,
                "gst": 1662.00,
                "total": 18282.00,
            },
            "safety": {"status": "DRAFT"},
            "review": {
                "reviewer": "Test Reviewer",
                "approved_at_utc": "2026-10-17T06:00:00+00:00",
            },
        }

    def test_approved_quotation_generates_pdf(self):
        pdf = build_approved_quotation_pdf(self.sample)

        self.assertIsInstance(pdf, bytes)
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertGreater(len(pdf), 1000)

    def test_pending_quotation_rejected(self):
        data = copy.deepcopy(self.sample)
        data["status"] = "PENDING"

        with self.assertRaises(ValueError):
            build_approved_quotation_pdf(data)

    def test_unsafe_quotation_rejected(self):
        for status in ("HOLD", "BLOCK"):
            with self.subTest(status=status):
                data = copy.deepcopy(self.sample)
                data["safety"]["status"] = status

                with self.assertRaises(ValueError):
                    build_approved_quotation_pdf(data)

    def test_missing_reviewer_rejected(self):
        data = copy.deepcopy(self.sample)
        data["review"]["reviewer"] = ""

        with self.assertRaises(ValueError):
            build_approved_quotation_pdf(data)

    def test_missing_timestamp_rejected(self):
        data = copy.deepcopy(self.sample)
        data["review"]["approved_at_utc"] = None

        with self.assertRaises(ValueError):
            build_approved_quotation_pdf(data)

    def test_empty_items_rejected(self):
        data = copy.deepcopy(self.sample)
        data["quotation"]["items"] = []

        with self.assertRaises(ValueError):
            build_approved_quotation_pdf(data)


if __name__ == "__main__":
    unittest.main()
