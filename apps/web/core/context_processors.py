from __future__ import annotations

from django.db.models import Count
from django.utils import timezone

from apps.web.core.models import AnalysisRecord, ContractRecord, FindingRecord


def admin_metrics(request) -> dict[str, object]:
    if not request.path.startswith("/admin/") or not request.user.is_authenticated or not request.user.is_staff:
        return {}

    today = timezone.localdate()
    top_findings = list(
        FindingRecord.objects.values("label")
        .annotate(total=Count("id"))
        .order_by("-total", "label")[:5]
    )
    risk_breakdown = {
        row["risk_level"]: row["total"]
        for row in AnalysisRecord.objects.values("risk_level").annotate(total=Count("id"))
    }

    return {
        "admin_metrics": {
            "contracts_today": ContractRecord.objects.filter(uploaded_at__date=today).count(),
            "analyses_today": AnalysisRecord.objects.filter(created_at__date=today).count(),
            "high_risk_total": AnalysisRecord.objects.filter(risk_level="high").count(),
            "top_findings": top_findings,
            "risk_breakdown": {
                "high": risk_breakdown.get("high", 0),
                "medium": risk_breakdown.get("medium", 0),
                "low": risk_breakdown.get("low", 0),
            },
        }
    }

