from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from apps.web.core.forms import ContractSubmissionForm, SignUpForm
from apps.web.core.models import AnalysisRecord, ContractRecord, FindingRecord
from apps.web.core.services import LegalEngineError, analyze_contract, analyze_contract_file


def _group_findings_by_clause(findings: list[FindingRecord]) -> list[dict[str, object]]:
    grouped: list[dict[str, object]] = []
    index_by_title: dict[str, int] = {}

    for finding in findings:
        clause_title = finding.clause_title.strip() or "Cláusula sin título"
        group_index = index_by_title.get(clause_title)
        if group_index is None:
            index_by_title[clause_title] = len(grouped)
            grouped.append({"clause_title": clause_title, "findings": [finding]})
        else:
            grouped[group_index]["findings"].append(finding)

    return grouped


def home(request: HttpRequest):
    if not request.user.is_authenticated:
        context = {
            "title": "LegalLens AI",
            "global_total_contracts": ContractRecord.objects.count(),
            "global_total_analyses": AnalysisRecord.objects.count(),
            "global_high_risk_count": AnalysisRecord.objects.filter(risk_level="high").count(),
        }
        return render(request, "core/home.html", context)

    user_contracts = ContractRecord.objects.filter(owner=request.user)
    user_analyses = AnalysisRecord.objects.filter(contract__owner=request.user)
    contract_rows = []
    for contract in user_contracts.prefetch_related("analyses")[:8]:
        analyses = list(contract.analyses.all())
        contract_rows.append(
            {
                "contract": contract,
                "contract_filename": contract.original_file.name.rsplit("/", 1)[-1] if contract.original_file else None,
                "uploaded_at_display": contract.uploaded_at.strftime("%d/%m/%Y %H:%M"),
                "latest_analysis": analyses[0] if analyses else None,
            }
        )
    recent_analyses = [
        {
            "analysis": analysis,
            "created_at_display": analysis.created_at.strftime("%d/%m/%Y %H:%M"),
        }
        for analysis in user_analyses.select_related("contract").prefetch_related("findings")[:8]
    ]
    context = {
        "title": "LegalLens AI",
        "total_contracts": user_contracts.count(),
        "total_analyses": user_analyses.count(),
        "high_risk_count": user_analyses.filter(risk_level="high").count(),
        "recent_contract_rows": contract_rows,
        "recent_analyses": recent_analyses,
    }
    return render(request, "core/dashboard.html", context)


def signup(request: HttpRequest):
    form = SignUpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Cuenta creada correctamente. Ya puedes empezar a auditar contratos.")
        return redirect("home")
    return render(request, "core/signup.html", {"form": form})


@login_required
def new_contract(request: HttpRequest):
    form = ContractSubmissionForm(request.POST or None, request.FILES or None)

    if request.method == "POST" and form.is_valid():
        payload = form.cleaned_data
        uploaded_file = payload.get("original_file")
        try:
            if uploaded_file:
                result = analyze_contract_file(
                    title=payload["title"],
                    contract_type=payload["contract_type"],
                    uploaded_file=uploaded_file,
                )
            else:
                result = analyze_contract(
                    title=payload["title"],
                    text=payload["raw_text"],
                    contract_type=payload["contract_type"],
                    source_type="text",
                )
        except LegalEngineError as exc:
            form.add_error(None, str(exc))
        else:
            with transaction.atomic():
                contract = ContractRecord.objects.create(
                    owner=request.user,
                    title=payload["title"],
                    client_name=payload["client_name"],
                    contract_type=payload["contract_type"],
                    source_type=result["source_type"],
                    raw_text=result["text"],
                    original_file=uploaded_file,
                )
                analysis = AnalysisRecord.objects.create(
                    contract=contract,
                    risk_level=result["risk_level"],
                    summary=result["summary"],
                    key_data=result["key_data"],
                    engine=result["engine"],
                    llm_used=result["llm_used"],
                )
                findings = [
                    FindingRecord(
                        analysis=analysis,
                        clause_title=finding["clause_title"],
                        severity=finding["severity"],
                        label=finding["label"],
                        evidence=finding["evidence"],
                        recommendation=finding["recommendation"],
                    )
                    for finding in result["findings"]
                ]
                if findings:
                    FindingRecord.objects.bulk_create(findings)

            messages.success(request, "Contrato analizado y guardado correctamente.")
            return redirect("analysis-detail", pk=analysis.pk)

    return render(request, "core/new_contract.html", {"form": form})


@login_required
def analysis_detail(request: HttpRequest, pk: int):
    analysis = get_object_or_404(
        AnalysisRecord.objects.select_related("contract").prefetch_related("findings"),
        pk=pk,
        contract__owner=request.user,
    )
    findings = list(analysis.findings.all())
    return render(
        request,
        "core/analysis_detail.html",
        {"analysis": analysis, "contract": analysis.contract, "grouped_findings": _group_findings_by_clause(findings)},
    )


def healthcheck(request: HttpRequest):
    return JsonResponse({"status": "ok", "service": "django-web"})

