from __future__ import annotations

import sys
from pathlib import Path
import unittest

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from packages.agents import LegalAnalysisAgent
from packages.domain import Document, RiskLevel


class LegalAnalysisAgentTests(unittest.TestCase):
    def test_detects_abusive_patterns(self) -> None:
        agent = LegalAnalysisAgent()
        document = Document(
            title="Suscripción",
            text="La empresa podrá modificar unilateralmente las condiciones. El consumidor renuncia a cualquier reembolso.",
        )

        result = agent.analyze(document)

        self.assertEqual(result.risk_level, RiskLevel.HIGH)
        self.assertGreaterEqual(len(result.findings), 1)
        self.assertEqual(result.engine, "rules")

    def test_returns_low_risk_when_no_match(self) -> None:
        agent = LegalAnalysisAgent()
        document = Document(
            title="Contrato equilibrado",
            text="Ambas partes podrán resolver el contrato con preaviso de 30 días y reembolso proporcional.",
        )

        result = agent.analyze(document)

        self.assertEqual(result.risk_level, RiskLevel.LOW)
        self.assertEqual(result.findings, [])

    def test_detects_rental_specific_pattern(self) -> None:
        agent = LegalAnalysisAgent()
        document = Document(
            title="Arrendamiento vivienda",
            contract_type="rental",
            text="Todos los gastos de la estructura de muros, tejados y fachadas correrán exclusivamente por cuenta del arrendatario.",
        )

        result = agent.analyze(document)

        self.assertEqual(result.risk_level, RiskLevel.HIGH)
        self.assertTrue(any(finding.label == "reparaciones_estructurales_inquilino" for finding in result.findings))
        self.assertEqual(result.key_data["tipo_contrato"], "rental")

    def test_detects_nda_specific_pattern(self) -> None:
        agent = LegalAnalysisAgent()
        document = Document(
            title="NDA crítica",
            contract_type="nda",
            text="La obligación de confidencialidad durará para siempre y por toda la eternidad para cualquier información conocida por el trabajador.",
        )

        result = agent.analyze(document)

        self.assertEqual(result.risk_level, RiskLevel.HIGH)
        self.assertTrue(any(finding.label == "duracion_infinita" for finding in result.findings))

    def test_uses_distinct_titles_for_distinct_numbered_nda_sections(self) -> None:
        agent = LegalAnalysisAgent()
        document = Document(
            title="NDA seccionada",
            contract_type="nda",
            text=(
                "I. Introducción general del acuerdo. "
                "VII. Absolutamente todo lo que el CLIENTE piense o diga es propiedad de la empresa. "
                "VIII. Texto transitorio sin hallazgos. "
                "X. Penalización de 50.000.000€ a CLIENTE por una filtración accidental."
            ),
        )

        result = agent.analyze(document)

        titles_by_label = {finding.label: finding.clause_title for finding in result.findings}
        self.assertEqual(titles_by_label["objeto_difuso_confidencialidad"], "Cláusula VII")
        self.assertEqual(titles_by_label["multa_desproporcionada"], "Cláusula X")

    def test_detects_nda_findings_even_if_contract_type_is_general(self) -> None:
        agent = LegalAnalysisAgent()
        document = Document(
            title="NDA mal tipada",
            contract_type="general",
            text=(
                "Acuerdo de confidencialidad entre CLIENTE y PROVEEDOR. "
                "VII. Absolutamente todo lo que el CLIENTE piense o diga es propiedad de la empresa. "
                "X. Penalización de 50.000.000€ a CLIENTE por una filtración accidental."
            ),
        )

        result = agent.analyze(document)

        labels = {finding.label for finding in result.findings}
        self.assertIn("objeto_difuso_confidencialidad", labels)
        self.assertIn("multa_desproporcionada", labels)


if __name__ == "__main__":
    unittest.main()

