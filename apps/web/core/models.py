from django.conf import settings
from django.db import models


class ContractRecord(models.Model):
    CONTRACT_TYPE_RENTAL = "rental"
    CONTRACT_TYPE_NDA = "nda"
    CONTRACT_TYPE_GENERAL = "general"

    CONTRACT_TYPE_CHOICES = (
        (CONTRACT_TYPE_RENTAL, "Alquiler"),
        (CONTRACT_TYPE_NDA, "NDA / Confidencialidad"),
        (CONTRACT_TYPE_GENERAL, "General"),
    )

    title = models.CharField(max_length=150)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="contracts", on_delete=models.CASCADE, null=True, blank=True)
    client_name = models.CharField(max_length=150, default="")
    contract_type = models.CharField(max_length=20, choices=CONTRACT_TYPE_CHOICES, default=CONTRACT_TYPE_RENTAL)
    source_type = models.CharField(max_length=50, default="text")
    raw_text = models.TextField(blank=True)
    original_file = models.FileField(upload_to="contracts/", blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-uploaded_at",)
        verbose_name = "Contrato"
        verbose_name_plural = "Contratos"

    def __str__(self) -> str:
        return self.title

    @property
    def latest_analysis(self):
        return self.analyses.order_by("-created_at").first()


class AnalysisRecord(models.Model):
    contract = models.ForeignKey(ContractRecord, related_name="analyses", on_delete=models.CASCADE)
    risk_level = models.CharField(max_length=20)
    summary = models.TextField()
    key_data = models.JSONField(default=dict, blank=True)
    engine = models.CharField(max_length=50, default="rules")
    llm_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Análisis"
        verbose_name_plural = "Análisis"

    def __str__(self) -> str:
        return f"{self.contract.title} - {self.risk_level}"


class FindingRecord(models.Model):
    analysis = models.ForeignKey(AnalysisRecord, related_name="findings", on_delete=models.CASCADE)
    clause_title = models.CharField(max_length=150)
    severity = models.CharField(max_length=20)
    label = models.CharField(max_length=100)
    evidence = models.TextField()
    recommendation = models.TextField()

    class Meta:
        verbose_name = "Hallazgo"
        verbose_name_plural = "Hallazgos"

    def __str__(self) -> str:
        return f"{self.clause_title} ({self.severity})"

