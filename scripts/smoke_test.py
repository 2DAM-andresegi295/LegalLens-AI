from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from packages.agents import LegalAnalysisAgent
from packages.domain import Document, RiskLevel


def run_agent_smoke_test() -> None:
    agent = LegalAnalysisAgent()
    document = Document(
        title="Contrato de prueba",
        text=(
            "La empresa podrá modificar unilateralmente las condiciones.\n\n"
            "El consumidor renuncia a cualquier reembolso."
        ),
    )
    result = agent.analyze(document)
    assert result.risk_level == RiskLevel.HIGH
    assert len(result.findings) >= 2


def run_django_check() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "apps.web.config.settings")
    import django
    from django.core.management import call_command

    django.setup()
    call_command("check")


def run_fastapi_import_check() -> None:
    from apps.api.app.main import app

    assert app.title == "LegalLens AI - Legal Engine"


if __name__ == "__main__":
    run_agent_smoke_test()
    run_fastapi_import_check()
    run_django_check()
    print("Validación rápida completada correctamente.")

