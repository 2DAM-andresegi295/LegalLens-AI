from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(slots=True)
class LLMResult:
    summary: str | None = None
    key_data: dict[str, str] | None = None
    findings: list[dict[str, str]] | None = None
    provider: str = "none"


class OptionalLegalLLM:
    def __init__(self) -> None:
        self.provider = os.getenv("LEGAL_LLM_PROVIDER", "none").lower().strip()
        self.base_url = os.getenv("LEGAL_LLM_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
        self.model = os.getenv("LEGAL_LLM_MODEL", "")
        self.api_key = os.getenv("LEGAL_LLM_API_KEY", "")
        self.timeout = float(os.getenv("LEGAL_LLM_TIMEOUT", "20"))

    def is_enabled(self) -> bool:
        if self.provider == "ollama":
            return bool(self.model and self.base_url)
        if self.provider == "openai":
            return bool(self.model and self.base_url and self.api_key)
        return False

    def analyze(self, *, text: str, focus: str, contract_type: str, existing_findings: list[dict[str, str]]) -> LLMResult | None:
        if not self.is_enabled():
            return None

        prompt = self._build_prompt(text=text, focus=focus, contract_type=contract_type, existing_findings=existing_findings)
        try:
            if self.provider == "ollama":
                content = self._call_ollama(prompt)
            elif self.provider == "openai":
                content = self._call_openai(prompt)
            else:
                return None
        except (httpx.HTTPError, ValueError, KeyError):
            return None

        parsed = self._extract_json(content)
        if not parsed:
            return None
        summary = parsed.get("summary")
        key_data = parsed.get("key_data")
        findings = parsed.get("findings")
        return LLMResult(
            summary=summary if isinstance(summary, str) else None,
            key_data=key_data if isinstance(key_data, dict) else {},
            findings=findings if isinstance(findings, list) else [],
            provider=self.provider,
        )

    def _call_ollama(self, prompt: str) -> str:
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                f"{self.base_url}/api/generate",
                json={"model": self.model, "prompt": prompt, "stream": False},
            )
            response.raise_for_status()
            return response.json()["response"]

    def _call_openai(self, prompt: str) -> str:
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": "Eres un auditor legal que responde exclusivamente en JSON válido."},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.1,
                },
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]

    @staticmethod
    def _build_prompt(*, text: str, focus: str, contract_type: str, existing_findings: list[dict[str, str]]) -> str:
        return (
            "Analiza el siguiente contrato y devuelve SOLO JSON con esta forma: "
            '{"summary": "...", "key_data": {"firmante": "..."}, "findings": ['
            '{"label": "...", "severity": "low|medium|high", "evidence": "...", "recommendation": "..."}]}. '
            f"Tipo de contrato: {contract_type}. Foco jurídico: {focus}. "
            f"Hallazgos previos por reglas: {json.dumps(existing_findings, ensure_ascii=False)}. "
            f"Texto del contrato:\n{text[:6000]}"
        )

    @staticmethod
    def _extract_json(content: str) -> dict[str, Any] | None:
        fenced_match = re.search(r"```json\s*({.*})\s*```", content, re.DOTALL)
        if fenced_match:
            content = fenced_match.group(1)
        else:
            raw_match = re.search(r"({.*})", content, re.DOTALL)
            if raw_match:
                content = raw_match.group(1)

        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            return None
        if not isinstance(parsed, dict):
            return None
        return parsed


