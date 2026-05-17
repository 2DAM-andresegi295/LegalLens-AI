from __future__ import annotations

import re
from collections import OrderedDict

from packages.domain import Document

DNI_PATTERN = re.compile(r"\b\d{8}[A-Z]\b", re.IGNORECASE)
AMOUNT_PATTERN = re.compile(r"\b(?:\d{1,3}(?:[.,]\d{3})+|\d+)(?:[.,]\d{2})?\s?(?:€|euros?)\b", re.IGNORECASE)
DATE_PATTERN = re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b|\b\d{1,2}\s+de\s+[a-záéíóúñ]+\s+de\s+\d{4}\b", re.IGNORECASE)
LABEL_PATTERNS = (
    ("arrendador", re.compile(r"(?:ARRENDADOR|EMPRESA|EMISOR|PROPIETARIO)\s*[:.-]\s*([A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑáéíóúñ\s]{3,80})")),
    ("arrendatario", re.compile(r"(?:ARRENDATARIO|RECEPTOR|TRABAJADOR|CLIENTE)\s*[:.-]\s*([A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑáéíóúñ\s]{3,80})")),
)


def extract_key_data(document: Document) -> dict[str, str]:
    text = document.text
    extracted: OrderedDict[str, str] = OrderedDict()

    for label, pattern in LABEL_PATTERNS:
        match = pattern.search(text)
        if match:
            extracted[label] = _normalize(match.group(1))

    dni_match = DNI_PATTERN.search(text)
    if dni_match:
        extracted["dni_identificado"] = dni_match.group(0).upper()

    first_date = DATE_PATTERN.search(text)
    if first_date:
        extracted["fecha_detectada"] = _normalize(first_date.group(0))

    first_amount = AMOUNT_PATTERN.search(text)
    if first_amount:
        extracted["importe_detectado"] = _normalize(first_amount.group(0))

    extracted.setdefault("tipo_contrato", document.contract_type)
    extracted.setdefault("origen", document.source_type)
    return dict(extracted)


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()

