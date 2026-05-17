from __future__ import annotations

import sys
from io import BytesIO
from pathlib import Path
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from reportlab.pdfgen import canvas

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from apps.api.app.main import app


class ApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_healthcheck(self) -> None:
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_analyze_endpoint(self) -> None:
        payload = {
            "title": "Contrato de suscripción",
            "text": "La empresa podrá modificar unilateralmente las condiciones. El consumidor renuncia a cualquier reembolso.",
            "contract_type": "general",
            "source_type": "text",
        }

        response = self.client.post("/v1/analyze", json=payload)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["risk_level"], "high")
        self.assertIn("key_data", response.json())

    def test_analyze_endpoint_supports_contract_type(self) -> None:
        payload = {
            "title": "NDA",
            "text": "La obligación de confidencialidad durará para siempre y por toda la eternidad.",
            "contract_type": "nda",
            "source_type": "text",
        }

        response = self.client.post("/v1/analyze", json=payload)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["risk_level"], "high")

    def test_analyze_file_endpoint(self) -> None:
        pdf_content = _build_pdf(
            "ARRENDADOR: Marta López\nARRENDATARIO: Carlos Díaz\n"
            "Todos los gastos de estructura de muros y tejados y fachadas correrán por cuenta del arrendatario."
        )

        response = self.client.post(
            "/v1/analyze-file",
            data={"title": "Contrato PDF", "contract_type": "rental"},
            files={"file": ("contrato.pdf", pdf_content, "application/pdf")},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["source_type"], "pdf")
        self.assertEqual(response.json()["risk_level"], "high")

    def test_contract_analysis_falls_back_locally_when_fastapi_is_unavailable(self) -> None:
        from apps.web.core.services import analyze_contract

        with patch("apps.web.core.services.LegalEngineClient._candidate_base_urls", return_value=()):
            result = analyze_contract(
                title="Contrato local",
                text="La empresa podrá modificar unilateralmente las condiciones. El consumidor renuncia a cualquier reembolso.",
                contract_type="general",
            )

        self.assertEqual(result["risk_level"], "high")
        self.assertEqual(result["engine"], "local-fallback")
        self.assertTrue(result["findings"])


def _build_pdf(text: str) -> bytes:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer)
    text_object = pdf.beginText(40, 800)
    for line in text.splitlines():
        text_object.textLine(line)
    pdf.drawText(text_object)
    pdf.save()
    return buffer.getvalue()


if __name__ == "__main__":
    unittest.main()

