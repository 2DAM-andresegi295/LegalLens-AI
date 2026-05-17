from __future__ import annotations
from dataclasses import dataclass, field
import os
from typing import Any

import httpx
from django.conf import settings

from apps.api.app.services.pdf import PDFExtractionError, extract_text_from_pdf
from packages.agents import LegalAnalysisAgent
from packages.domain import Document


class LegalEngineError(Exception):
    pass


@dataclass(slots=True)
class LegalEngineClient:
    base_url: str | None = None
    timeout: float | None = None
    local_agent: LegalAnalysisAgent = field(default_factory=LegalAnalysisAgent)

    def __post_init__(self) -> None:
        if self.base_url is None:
            self.base_url = self._runtime_setting("LEGAL_ENGINE_BASE_URL", "http://127.0.0.1:8001")
        if self.timeout is None:
            self.timeout = float(self._runtime_setting("LEGAL_ENGINE_TIMEOUT", 20))

    def _candidate_base_urls(self) -> tuple[str, ...]:
        candidates: list[str] = []
        for value in (
            self.base_url,
            self._runtime_setting("LEGAL_ENGINE_BASE_URL", None),
            "http://ai_engine:8001",
            "http://127.0.0.1:8001",
            "http://localhost:8001",
        ):
            normalized = (value or "").strip()
            if normalized and normalized not in candidates:
                candidates.append(normalized)
        return tuple(candidates)

    @staticmethod
    def _runtime_setting(name: str, default: Any) -> Any:
        if settings.configured:
            return getattr(settings, name, default)
        return os.getenv(name, default)

    def analyze_text(self, *, title: str, text: str, contract_type: str, source_type: str = "text") -> dict[str, Any]:
        payload = {
            "title": title,
            "text": text,
            "contract_type": contract_type,
            "source_type": source_type,
        }
        return self._post_json(endpoint_path="/v1/analyze", payload=payload)

    def analyze_file(self, *, title: str, contract_type: str, uploaded_file) -> dict[str, Any]:
        file_bytes = uploaded_file.read()
        uploaded_file.seek(0)
        files = {"file": (uploaded_file.name, file_bytes, uploaded_file.content_type or "application/pdf")}
        data = {"title": title, "contract_type": contract_type}

        return self._post_multipart(endpoint_path="/v1/analyze-file", data=data, files=files)

    def _post_json(self, *, endpoint_path: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request_with_fallback(endpoint_path=endpoint_path, json=payload)

    def _post_multipart(self, *, endpoint_path: str, data: dict[str, Any], files: dict[str, Any]) -> dict[str, Any]:
        return self._request_with_fallback(endpoint_path=endpoint_path, data=data, files=files)

    def _request_with_fallback(
        self,
        *,
        endpoint_path: str,
        json: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        files: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        last_timeout_exc: httpx.TimeoutException | None = None
        last_request_exc: httpx.RequestError | None = None

        for base_url in self._candidate_base_urls():
            endpoint = f"{base_url.rstrip('/')}{endpoint_path}"
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.post(endpoint, json=json, data=data, files=files)
                    return self._handle_response(response)
            except httpx.TimeoutException as exc:
                last_timeout_exc = exc
            except httpx.RequestError as exc:
                last_request_exc = exc

        if last_timeout_exc is not None:
            return self._local_fallback_from_error("El motor de análisis no respondió a tiempo. Inténtalo de nuevo.", last_timeout_exc, endpoint_path, json, data, files)
        if last_request_exc is not None:
            return self._local_fallback_from_error("No se pudo conectar con el motor de análisis. Revisa que FastAPI esté activo.", last_request_exc, endpoint_path, json, data, files)

        return self._local_fallback_from_error("No se pudo conectar con el motor de análisis. Revisa que FastAPI esté activo.", None, endpoint_path, json, data, files)

    def _local_fallback_from_error(
        self,
        message: str,
        exc: Exception | None,
        endpoint_path: str,
        json: dict[str, Any] | None,
        data: dict[str, Any] | None,
        files: dict[str, Any] | None,
    ) -> dict[str, Any]:
        try:
            return self._local_fallback(endpoint_path=endpoint_path, json=json, data=data, files=files)
        except LegalEngineError:
            if exc is not None:
                raise LegalEngineError(message) from exc
            raise LegalEngineError(message)

    def _local_fallback(
        self,
        *,
        endpoint_path: str,
        json: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        files: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if endpoint_path.endswith("/analyze") and json is not None:
            document = Document(
                title=str(json.get("title", "Contrato")),
                text=str(json.get("text", "")),
                source_type=str(json.get("source_type", "text")),
                contract_type=str(json.get("contract_type", "general")),
            )
            result = self.local_agent.analyze(document)
            payload = result.to_dict()
            payload["engine"] = "local-fallback"
            return payload

        if endpoint_path.endswith("/analyze-file") and data is not None and files is not None:
            title = str(data.get("title", "Contrato"))
            contract_type = str(data.get("contract_type", "general"))
            file_info = files.get("file")
            if not isinstance(file_info, tuple) or len(file_info) < 2:
                raise LegalEngineError("No se pudo leer el archivo PDF para el análisis local.")

            file_bytes = file_info[1]
            if not isinstance(file_bytes, (bytes, bytearray)):
                raise LegalEngineError("No se pudo leer el archivo PDF para el análisis local.")

            try:
                text = extract_text_from_pdf(bytes(file_bytes))
            except PDFExtractionError as exc:
                raise LegalEngineError(str(exc)) from exc

            document = Document(title=title, text=text, source_type="pdf", contract_type=contract_type)
            result = self.local_agent.analyze(document)
            payload = result.to_dict()
            payload["engine"] = "local-fallback"
            return payload

        raise LegalEngineError("No se pudo ejecutar el análisis local de respaldo.")

    @staticmethod
    def _handle_response(response: httpx.Response) -> dict[str, Any]:
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = "El motor de análisis devolvió un error inesperado."
            try:
                payload = response.json()
                detail = payload.get("detail", detail)
            except ValueError:
                pass
            raise LegalEngineError(detail) from exc

        try:
            data = response.json()
        except ValueError as exc:
            raise LegalEngineError("La respuesta del motor de análisis no tiene un formato válido.") from exc

        required_keys = {"risk_level", "summary", "findings", "key_data", "text", "source_type", "engine", "llm_used"}
        if not required_keys.issubset(data):
            raise LegalEngineError("La respuesta del motor de análisis está incompleta.")
        return data


def analyze_contract(*, title: str, text: str, contract_type: str, source_type: str = "text") -> dict[str, Any]:
    return LegalEngineClient().analyze_text(
        title=title,
        text=text,
        contract_type=contract_type,
        source_type=source_type,
    )


def analyze_contract_file(*, title: str, contract_type: str, uploaded_file) -> dict[str, Any]:
    return LegalEngineClient().analyze_file(
        title=title,
        contract_type=contract_type,
        uploaded_file=uploaded_file,
    )


