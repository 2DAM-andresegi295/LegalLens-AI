from django.urls import path

from apps.web.core.views import analysis_detail, healthcheck, home, new_contract, signup

urlpatterns = [
    path("", home, name="home"),
    path("accounts/signup/", signup, name="signup"),
    path("contracts/new/", new_contract, name="contract-create"),
    path("analyses/<int:pk>/", analysis_detail, name="analysis-detail"),
    path("health/", healthcheck, name="health"),
]

