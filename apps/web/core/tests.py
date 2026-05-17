from __future__ import annotations

from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from apps.web.core.models import AnalysisRecord, ContractRecord, FindingRecord
from apps.web.core.services import LegalEngineError


class ContractFlowTests(TestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user(username="abogada", password="segura123")

    @patch("apps.web.core.views.analyze_contract")
    def test_creates_contract_and_persists_analysis(self, analyze_contract_mock) -> None:
        analyze_contract_mock.return_value = {
            "title": "Contrato de alquiler",
            "risk_level": "high",
            "summary": "Se detectaron cláusulas problemáticas.",
            "key_data": {"arrendador": "María Pérez"},
            "source_type": "text",
            "text": "La estructura de muros correrá por cuenta del arrendatario durante toda la vigencia del contrato.",
            "engine": "rules",
            "llm_used": False,
            "findings": [
                {
                    "clause_title": "Cláusula 1",
                    "severity": "high",
                    "label": "reparaciones_estructurales_inquilino",
                    "evidence": "La estructura de muros correrá por cuenta del arrendatario.",
                    "recommendation": "Revisar si se traslada al inquilino una obligación de conservación que corresponde al arrendador.",
                }
            ],
        }

        self.client.force_login(self.user)

        response = self.client.post(
            reverse("contract-create"),
            data={
                "title": "Contrato de alquiler",
                "client_name": "Ana García",
                "contract_type": ContractRecord.CONTRACT_TYPE_RENTAL,
                "raw_text": "La estructura de muros correrá por cuenta del arrendatario durante toda la vigencia del contrato.",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(ContractRecord.objects.count(), 1)
        self.assertEqual(AnalysisRecord.objects.count(), 1)
        self.assertEqual(FindingRecord.objects.count(), 1)
        self.assertContains(response, "Se detectaron cláusulas problemáticas.")
        self.assertEqual(ContractRecord.objects.first().owner, self.user)

    @patch("apps.web.core.views.analyze_contract")
    def test_does_not_persist_when_engine_fails(self, analyze_contract_mock) -> None:
        analyze_contract_mock.side_effect = LegalEngineError("FastAPI no disponible")

        self.client.force_login(self.user)

        response = self.client.post(
            reverse("contract-create"),
            data={
                "title": "Contrato fallido",
                "client_name": "Cliente Demo",
                "contract_type": ContractRecord.CONTRACT_TYPE_NDA,
                "raw_text": "Este texto es suficientemente largo para pasar validación del formulario, pero simulará un error del motor.",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(ContractRecord.objects.count(), 0)
        self.assertContains(response, "FastAPI no disponible")

    @patch("apps.web.core.views.analyze_contract_file")
    def test_creates_contract_from_pdf(self, analyze_contract_file_mock) -> None:
        analyze_contract_file_mock.return_value = {
            "title": "NDA PDF",
            "risk_level": "medium",
            "summary": "Se detectaron cláusulas relevantes en el PDF.",
            "key_data": {"importe_detectado": "100.000 €"},
            "source_type": "pdf",
            "text": "Texto extraído del PDF",
            "engine": "rules",
            "llm_used": False,
            "findings": [],
        }

        self.client.force_login(self.user)
        file = SimpleUploadedFile("nda.pdf", b"%PDF-1.4 fake pdf", content_type="application/pdf")

        response = self.client.post(
            reverse("contract-create"),
            data={
                "title": "NDA PDF",
                "client_name": "Empresa Demo",
                "contract_type": ContractRecord.CONTRACT_TYPE_NDA,
                "original_file": file,
                "raw_text": "",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(ContractRecord.objects.count(), 1)
        self.assertEqual(ContractRecord.objects.first().source_type, "pdf")

    def test_rejects_contracts_with_too_little_text(self) -> None:
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("contract-create"),
            data={
                "title": "Contrato corto",
                "client_name": "Cliente Demo",
                "contract_type": ContractRecord.CONTRACT_TYPE_GENERAL,
                "raw_text": "Muy corto.",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(ContractRecord.objects.count(), 0)
        self.assertContains(response, "Incluye al menos 50 caracteres")

    def test_contract_create_requires_authentication(self) -> None:
        response = self.client.get(reverse("contract-create"))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.headers["Location"])

    def test_dashboard_lists_only_user_contracts(self) -> None:
        other_user = User.objects.create_user(username="otro", password="segura123")
        own_contract = ContractRecord.objects.create(
            owner=self.user,
            title="Contrato propio",
            client_name="Cliente A",
            contract_type=ContractRecord.CONTRACT_TYPE_GENERAL,
            raw_text="Texto suficientemente largo para que el contrato exista en el panel privado.",
        )
        own_analysis = AnalysisRecord.objects.create(
            contract=own_contract,
            risk_level="medium",
            summary="Resumen de prueba.",
            key_data={},
            engine="rules",
            llm_used=False,
        )
        ContractRecord.objects.create(
            owner=other_user,
            title="Contrato ajeno",
            client_name="Cliente B",
            contract_type=ContractRecord.CONTRACT_TYPE_GENERAL,
            raw_text="Otro texto suficientemente largo para quedar fuera del panel del usuario autenticado.",
        )

        self.client.force_login(self.user)
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Contrato propio")
        self.assertContains(response, reverse("analysis-detail", args=[own_analysis.pk]))
        self.assertNotContains(response, "Contrato ajeno")


class AdminDashboardTests(TestCase):
    def setUp(self) -> None:
        self.admin_user = User.objects.create_superuser(username="socia", email="socia@example.com", password="admin12345")

    def test_admin_index_shows_global_metrics(self) -> None:
        contract = ContractRecord.objects.create(
            owner=self.admin_user,
            title="Contrato admin",
            client_name="Cliente Admin",
            contract_type=ContractRecord.CONTRACT_TYPE_NDA,
            raw_text="Texto suficientemente largo para el contrato del panel de administración.",
        )
        analysis = AnalysisRecord.objects.create(
            contract=contract,
            risk_level="high",
            summary="Resumen admin.",
            key_data={},
            engine="rules",
            llm_used=False,
        )
        FindingRecord.objects.create(
            analysis=analysis,
            clause_title="Cláusula X",
            severity="high",
            label="multa_desproporcionada",
            evidence="Penalización de prueba.",
            recommendation="Revisar penalización.",
        )

        self.client.force_login(self.admin_user)
        response = self.client.get("/admin/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Resumen global de LegalLens AI")
        self.assertContains(response, "Contratos analizados hoy")
        self.assertContains(response, "multa_desproporcionada")


class AnalysisDetailGroupingTests(TestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user(username="analista", password="segura123")
        self.contract = ContractRecord.objects.create(
            owner=self.user,
            title="Contrato agrupado",
            client_name="Cliente Agrupado",
            contract_type=ContractRecord.CONTRACT_TYPE_RENTAL,
            raw_text="Texto suficiente para el detalle de análisis.",
        )
        self.analysis = AnalysisRecord.objects.create(
            contract=self.contract,
            risk_level="high",
            summary="Resumen agrupado.",
            key_data={},
            engine="rules",
            llm_used=False,
        )
        FindingRecord.objects.create(
            analysis=self.analysis,
            clause_title="Cláusula 21",
            severity="high",
            label="acceso_ilimitado_arrendador",
            evidence="El casero puede entrar a inspeccionar sin aviso previo.",
            recommendation="Comprobar si se vulnera la intimidad domiciliaria del arrendatario.",
        )
        FindingRecord.objects.create(
            analysis=self.analysis,
            clause_title="Cláusula 21",
            severity="high",
            label="desahucio_privado",
            evidence="El dueño puede cambiar la cerradura si el inquilino se retrasa 1 día.",
            recommendation="Invalidar cualquier autotutela privada y remitir a cauces judiciales legales.",
        )

    def test_analysis_detail_groups_duplicate_clause_titles(self) -> None:
        self.client.force_login(self.user)
        response = self.client.get(reverse("analysis-detail", args=[self.analysis.pk]))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")
        self.assertEqual(content.count("Cláusula 21"), 1)
        self.assertIn("ALTO", content)
        self.assertContains(response, "acceso_ilimitado_arrendador")
        self.assertContains(response, "desahucio_privado")


class AnalysisDetailGroupingTests(TestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user(username="analista", password="segura123")
        self.contract = ContractRecord.objects.create(
            owner=self.user,
            title="Contrato agrupado",
            client_name="Cliente Agrupado",
            contract_type=ContractRecord.CONTRACT_TYPE_RENTAL,
            raw_text="Texto suficiente para el detalle de análisis.",
        )
        self.analysis = AnalysisRecord.objects.create(
            contract=self.contract,
            risk_level="high",
            summary="Resumen agrupado.",
            key_data={},
            engine="rules",
            llm_used=False,
        )
        FindingRecord.objects.create(
            analysis=self.analysis,
            clause_title="Cláusula 21",
            severity="high",
            label="acceso_ilimitado_arrendador",
            evidence="El casero puede entrar a inspeccionar sin aviso previo.",
            recommendation="Comprobar si se vulnera la intimidad domiciliaria del arrendatario.",
        )
        FindingRecord.objects.create(
            analysis=self.analysis,
            clause_title="Cláusula 21",
            severity="high",
            label="desahucio_privado",
            evidence="El dueño puede cambiar la cerradura si el inquilino se retrasa 1 día.",
            recommendation="Invalidar cualquier autotutela privada y remitir a cauces judiciales legales.",
        )

    def test_analysis_detail_groups_duplicate_clause_titles(self) -> None:
        self.client.force_login(self.user)
        response = self.client.get(reverse("analysis-detail", args=[self.analysis.pk]))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")
        self.assertEqual(content.count("Cláusula 21"), 1)
        self.assertIn("ALTO", content)
        self.assertContains(response, "acceso_ilimitado_arrendador")
        self.assertContains(response, "desahucio_privado")


