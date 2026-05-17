from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from apps.web.core.models import ContractRecord


class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True, label="Correo electrónico")

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "password1", "password2")


class ContractSubmissionForm(forms.ModelForm):
    original_file = forms.FileField(required=False, label="Archivo PDF")

    class Meta:
        model = ContractRecord
        fields = ("title", "client_name", "contract_type", "original_file", "raw_text")
        labels = {
            "title": "Título del contrato",
            "client_name": "Cliente",
            "contract_type": "Tipo de contrato",
            "original_file": "Archivo PDF",
            "raw_text": "Texto del contrato",
        }
        widgets = {
            "raw_text": forms.Textarea(attrs={"rows": 14, "placeholder": "Pega aquí el texto del contrato si no quieres subir un PDF."}),
        }

    def clean(self) -> dict[str, object]:
        cleaned_data = super().clean()
        raw_text = (cleaned_data.get("raw_text") or "").strip()
        original_file = cleaned_data.get("original_file")

        if not raw_text and not original_file:
            raise forms.ValidationError("Debes pegar texto o subir un PDF para lanzar la auditoría.")

        if raw_text and len(raw_text) < 50:
            self.add_error("raw_text", "Incluye al menos 50 caracteres para poder analizar el contrato.")

        if original_file and not original_file.name.lower().endswith(".pdf"):
            self.add_error("original_file", "En esta fase solo se admiten archivos PDF.")

        cleaned_data["raw_text"] = raw_text
        return cleaned_data

