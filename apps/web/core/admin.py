from django.contrib import admin

from apps.web.core.models import AnalysisRecord, ContractRecord, FindingRecord


class FindingInline(admin.TabularInline):
    model = FindingRecord
    extra = 0


@admin.register(AnalysisRecord)
class AnalysisRecordAdmin(admin.ModelAdmin):
    list_display = ("contract", "risk_level", "engine", "llm_used", "created_at")
    list_filter = ("risk_level", "engine", "llm_used", "created_at")
    search_fields = ("contract__title", "summary")
    inlines = [FindingInline]


class AnalysisInline(admin.TabularInline):
    model = AnalysisRecord
    extra = 0


@admin.register(ContractRecord)
class ContractRecordAdmin(admin.ModelAdmin):
    list_display = ("title", "owner", "client_name", "contract_type", "source_type", "uploaded_at")
    list_filter = ("contract_type", "source_type", "uploaded_at")
    search_fields = ("title", "client_name", "raw_text", "owner__username")
    inlines = [AnalysisInline]


@admin.register(FindingRecord)
class FindingRecordAdmin(admin.ModelAdmin):
    list_display = ("clause_title", "severity", "label")
    list_filter = ("severity", "label")
    search_fields = ("clause_title", "evidence", "recommendation")

