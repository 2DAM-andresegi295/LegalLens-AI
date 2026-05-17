from __future__ import annotations

import unicodedata

from packages.agents.base import BaseAgent
from packages.contracts import create_contract
from packages.entity_extraction import extract_key_data
from packages.domain import AnalysisResult, ClauseFinding, DetectionRule, Document, RiskLevel
from packages.llm import OptionalLegalLLM


class LegalAnalysisAgent(BaseAgent):
    COMMON_RULES: tuple[DetectionRule, ...] = (
        DetectionRule(
            label="modificacion_unilateral",
            terms=("modificar unilateralmente", "cambiar unilateralmente", "a su sola discrecion", "modificar las condiciones sin previo aviso"),
            severity=RiskLevel.HIGH,
            recommendation="Validar si existe equilibrio contractual y mecanismos de información previa.",
        ),
        DetectionRule(
            label="renuncia_reembolso",
            terms=("sin derecho a reembolso", "renuncia a cualquier reembolso", "no habra devolucion"),
            severity=RiskLevel.HIGH,
            recommendation="Revisar si la exclusión del reembolso vulnera derechos básicos del consumidor.",
        ),
        DetectionRule(
            label="penalizacion_excesiva",
            terms=("penalizacion del 100%", "multa excesiva", "cargo desproporcionado", "sin necesidad de mediacion judicial"),
            severity=RiskLevel.MEDIUM,
            recommendation="Comprobar la proporcionalidad de la penalización respecto al incumplimiento.",
        ),
        DetectionRule(
            label="renuncia_garantia",
            terms=("renuncia a la garantia", "sin garantia legal", "exclusion total de garantia"),
            severity=RiskLevel.HIGH,
            recommendation="Verificar si se intenta limitar una garantía imperativa no renunciable.",
        ),
    )

    def __init__(self) -> None:
        self.llm = OptionalLegalLLM()

    def analyze(self, document: Document) -> AnalysisResult:
        findings: list[ClauseFinding] = []
        contract_class = create_contract(document.contract_type)
        inferred_contract_class = create_contract(self._infer_contract_type(document))
        rules = self._merge_rules(
            self.COMMON_RULES,
            contract_class.get_rules(),
            inferred_contract_class.get_rules(),
        )

        for index, clause_block in enumerate(document.clause_blocks(), start=1):
            normalized_clause = self._normalize_text(clause_block.text)
            for rule in rules:
                if any(self._normalize_text(term) in normalized_clause for term in rule.terms):
                    findings.append(
                        ClauseFinding(
                            clause_title=clause_block.title or f"Cláusula {index}",
                            severity=rule.severity,
                            label=rule.label,
                            evidence=clause_block.text.strip(),
                            recommendation=rule.recommendation,
                        )
                    )

        key_data = extract_key_data(document)
        llm_used = False
        engine = "rules"
        llm_result = self.llm.analyze(
            text=document.text,
            focus=contract_class.get_focus(),
            contract_type=document.contract_type,
            existing_findings=[finding.to_dict() for finding in findings],
        )
        if llm_result:
            llm_used = True
            engine = f"hybrid:{llm_result.provider}"
            if llm_result.summary:
                llm_summary = llm_result.summary.strip()
            else:
                llm_summary = None
            key_data.update({key: value for key, value in (llm_result.key_data or {}).items() if value})
            findings.extend(self._build_llm_findings(llm_result.findings or [], len(findings)))
        else:
            llm_summary = None

        risk_level = self._resolve_risk(findings)
        summary = llm_summary or self._build_summary(findings)
        return AnalysisResult(
            title=document.title,
            risk_level=risk_level,
            summary=summary,
            key_data=key_data,
            source_type=document.source_type,
            text=document.text,
            engine=engine,
            llm_used=llm_used,
            findings=findings,
        )

    @staticmethod
    def _resolve_risk(findings: list[ClauseFinding]) -> RiskLevel:
        if any(finding.severity == RiskLevel.HIGH for finding in findings):
            return RiskLevel.HIGH
        if findings:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW

    @staticmethod
    def _build_summary(findings: list[ClauseFinding]) -> str:
        if not findings:
            return "No se detectaron patrones abusivos en la primera revisión automatizada."
        if any(finding.severity == RiskLevel.HIGH for finding in findings):
            return "Se detectaron indicios que merecen revisión legal prioritaria."
        return "Se encontraron cláusulas que conviene revisar manualmente."

    @staticmethod
    def _normalize_text(value: str) -> str:
        normalized = unicodedata.normalize("NFD", value.casefold())
        return "".join(character for character in normalized if unicodedata.category(character) != "Mn")

    @staticmethod
    def _build_llm_findings(findings: list[dict[str, str]], offset: int) -> list[ClauseFinding]:
        built: list[ClauseFinding] = []
        for index, finding in enumerate(findings, start=1):
            evidence = finding.get("evidence", "").strip()
            if not evidence:
                continue
            severity = LegalAnalysisAgent._parse_risk(finding.get("severity", "medium"))
            built.append(
                ClauseFinding(
                    clause_title=finding.get("clause_title") or f"Hallazgo IA {offset + index}",
                    severity=severity,
                    label=finding.get("label", "hallazgo_llm"),
                    evidence=evidence,
                    recommendation=finding.get("recommendation", "Revisar manualmente con apoyo jurídico."),
                )
            )
        return built

    @staticmethod
    def _parse_risk(value: str) -> RiskLevel:
        normalized = value.casefold().strip()
        if normalized in {"high", "alto", "critico", "crítico"}:
            return RiskLevel.HIGH
        if normalized in {"low", "bajo"}:
            return RiskLevel.LOW
        return RiskLevel.MEDIUM

    @classmethod
    def _merge_rules(cls, *rule_groups: tuple[DetectionRule, ...]) -> tuple[DetectionRule, ...]:
        merged: list[DetectionRule] = []
        seen_labels: set[str] = set()
        for group in rule_groups:
            for rule in group:
                if rule.label in seen_labels:
                    continue
                seen_labels.add(rule.label)
                merged.append(rule)
        return tuple(merged)

    def _infer_contract_type(self, document: Document) -> str:
        normalized_text = self._normalize_text(document.text)

        nda_signals = (
            "acuerdo de confidencialidad",
            "informacion confidencial",
            "cliente",
            "proveedor",
            "deber de secreto",
        )
        rental_signals = (
            "arrendador",
            "arrendatario",
            "fianza",
            "renta",
            "vivienda",
        )

        nda_score = sum(signal in normalized_text for signal in nda_signals)
        rental_score = sum(signal in normalized_text for signal in rental_signals)

        if nda_score > rental_score and nda_score >= 2:
            return "nda"
        if rental_score > nda_score and rental_score >= 2:
            return "rental"
        return document.contract_type

