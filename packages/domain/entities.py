from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import re


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True, slots=True)
class DetectionRule:
    label: str
    terms: tuple[str, ...]
    severity: RiskLevel
    recommendation: str


@dataclass(slots=True)
class Document:
    title: str
    text: str
    source_type: str = "text"
    contract_type: str = "general"

    CLAUSE_HEADER_PATTERN = re.compile(r"(?i)^\s*(cl[áa]usula\s+[a-z0-9ivxlcdmáéíóúñ]+)")
    SECTION_HEADER_PATTERN = re.compile(r"^\s*([IVXLCDM]{1,7}|\d{1,2})\.\s+")

    def clauses(self) -> list[str]:
        return [block.text for block in self.clause_blocks()]

    def clause_blocks(self) -> list[ClauseBlock]:
        normalized_text = self._normalize_contract_text(self.text)
        header_blocks = self._split_by_detected_headers(normalized_text)
        if header_blocks:
            return header_blocks

        cleaned_blocks = [block.strip() for block in normalized_text.split("\n\n") if block.strip()]
        if cleaned_blocks:
            return [ClauseBlock(title=f"Cláusula {index}", text=block) for index, block in enumerate(cleaned_blocks, start=1)]

        fallback = [segment.strip() for segment in normalized_text.split(".") if segment.strip()]
        fallback_blocks = [f"{segment}." for segment in fallback] or [normalized_text.strip()]
        return [ClauseBlock(title=f"Cláusula {index}", text=block) for index, block in enumerate(fallback_blocks, start=1)]

    @classmethod
    def _normalize_contract_text(cls, text: str) -> str:
        normalized = text.replace("\r\n", "\n")
        normalized = re.sub(r"\n{3,}", "\n\n", normalized)
        normalized = re.sub(r"\s+(cl[áa]usula\s+[a-z0-9ivxlcdmáéíóúñ]+)", r"\n\n\1", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"\s+((?:[IVXLCDM]{1,7}|\d{1,2})\.\s+[A-ZÁÉÍÓÚÑ])", r"\n\n\1", normalized)
        normalized = re.sub(r"[ \t]+", " ", normalized)
        return normalized.strip()

    @classmethod
    def _split_by_detected_headers(cls, text: str) -> list[ClauseBlock]:
        blocks = [block.strip() for block in text.split("\n\n") if block.strip()]
        if not blocks:
            return []

        clause_blocks: list[ClauseBlock] = []
        for index, block in enumerate(blocks, start=1):
            title = cls._infer_clause_title(block, index)
            clause_blocks.append(ClauseBlock(title=title, text=block))

        detected_titles = [block for index, block in enumerate(clause_blocks, start=1) if block.title != f"Cláusula {index}"]
        return clause_blocks if detected_titles else []

    @classmethod
    def _infer_clause_title(cls, block: str, index: int) -> str:
        clause_match = cls.CLAUSE_HEADER_PATTERN.match(block)
        if clause_match:
            return cls._clean_title(clause_match.group(1))

        section_match = cls.SECTION_HEADER_PATTERN.match(block)
        if section_match:
            return f"Cláusula {section_match.group(1)}"

        return f"Cláusula {index}"

    @staticmethod
    def _clean_title(value: str) -> str:
        cleaned = re.sub(r"\s+", " ", value).strip(" .:-")
        return cleaned.title()


@dataclass(frozen=True, slots=True)
class ClauseBlock:
    title: str
    text: str


@dataclass(slots=True)
class ClauseFinding:
    clause_title: str
    severity: RiskLevel
    label: str
    evidence: str
    recommendation: str

    def to_dict(self) -> dict[str, str]:
        return {
            "clause_title": self.clause_title,
            "severity": self.severity.value,
            "label": self.label,
            "evidence": self.evidence,
            "recommendation": self.recommendation,
        }


@dataclass(slots=True)
class AnalysisResult:
    title: str
    risk_level: RiskLevel
    summary: str
    key_data: dict[str, str] = field(default_factory=dict)
    source_type: str = "text"
    text: str = ""
    engine: str = "rules"
    llm_used: bool = False
    findings: list[ClauseFinding] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "title": self.title,
            "risk_level": self.risk_level.value,
            "summary": self.summary,
            "key_data": self.key_data,
            "source_type": self.source_type,
            "text": self.text,
            "engine": self.engine,
            "llm_used": self.llm_used,
            "findings": [finding.to_dict() for finding in self.findings],
        }

