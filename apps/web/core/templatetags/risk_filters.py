from __future__ import annotations

from django import template

register = template.Library()

RISK_LABELS = {
    "low": "BAJO",
    "medium": "MEDIO",
    "high": "ALTO",
}


@register.filter(name="risk_label")
def risk_label(value: object) -> str:
    normalized = str(value).strip().lower()
    return RISK_LABELS.get(normalized, str(value).upper())

